import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { createServer, connect } from 'node:net';
import { createProxy, parseAllow, isBlockedAddress } from '../proxy.ts';
import { tmp } from './tmp.ts';
import type { AddressInfo, Server, Socket } from 'node:net';

const listen = (server: Server) => new Promise<number>((r) => server.listen(0, '127.0.0.1', () => r((server.address() as AddressInfo).port)));

function rawRequest(port: number, text: string) {
  return new Promise<{ sock: Socket; head: string }>((resolve, reject) => {
    const sock = connect(port, '127.0.0.1', () => sock.write(text));
    let data = '';
    sock.on('data', (d) => {
      data += d;
      if (data.includes('\r\n\r\n')) resolve({ sock, head: data });
    });
    sock.on('error', reject);
  });
}

test('parseAllow defaults to port 443 and lowercases', () => {
  assert.deepEqual([...parseAllow('API.anthropic.com, registry.npmjs.org ,127.0.0.1:8080,')], ['api.anthropic.com:443', 'registry.npmjs.org:443', '127.0.0.1:8080']);
});

test('tunnels an allowed CONNECT', async () => {
  const echo = createServer((s) => s.pipe(s));
  const echoPort = await listen(echo);
  const logs: Record<string, unknown>[] = [];
  const proxy = createProxy({ allow: parseAllow(`127.0.0.1:${echoPort}`), log: (o) => logs.push(o) });
  const proxyPort = await listen(proxy);
  try {
    const { sock, head } = await rawRequest(proxyPort, `CONNECT 127.0.0.1:${echoPort} HTTP/1.1\r\nHost: 127.0.0.1:${echoPort}\r\n\r\n`);
    assert.match(head, /^HTTP\/1\.1 200/);
    const echoed = await new Promise((r) => { sock.once('data', (d) => r(String(d))); sock.write('ping'); });
    assert.equal(echoed, 'ping');
    sock.destroy();
    assert.ok(logs.some((l) => l.event === 'allowed'));
  } finally {
    proxy.close();
    echo.close();
  }
});

test('refuses a CONNECT that is not allowlisted', async () => {
  const logs: Record<string, unknown>[] = [];
  const proxy = createProxy({ allow: parseAllow('api.anthropic.com'), log: (o) => logs.push(o) });
  const port = await listen(proxy);
  try {
    const { sock, head } = await rawRequest(port, 'CONNECT evil.example.com:443 HTTP/1.1\r\nHost: evil.example.com:443\r\n\r\n');
    assert.match(head, /^HTTP\/1\.1 403/);
    sock.destroy();
    assert.deepEqual(logs.at(-1), { event: 'refused', target: 'evil.example.com:443' });
  } finally {
    proxy.close();
  }
});

test('refuses plain HTTP proxying', async () => {
  const proxy = createProxy({ allow: parseAllow('example.com'), log: () => {} });
  const port = await listen(proxy);
  try {
    const { sock, head } = await rawRequest(port, 'GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n');
    assert.match(head, /^HTTP\/1\.1 405/);
    sock.destroy();
  } finally {
    proxy.close();
  }
});

test('isBlockedAddress rejects private ranges', () => {
  // IPv4 private ranges
  assert.ok(isBlockedAddress('127.0.0.1'));
  assert.ok(isBlockedAddress('10.1.2.3'));
  assert.ok(isBlockedAddress('172.20.0.1'));
  assert.ok(isBlockedAddress('192.168.1.1'));
  assert.ok(isBlockedAddress('169.254.169.254'));
  assert.ok(isBlockedAddress('100.64.0.1'));
  // IPv6 private ranges
  assert.ok(isBlockedAddress('::1'));
  assert.ok(isBlockedAddress('fd00::1'));
  assert.ok(isBlockedAddress('fe80::1'));
  assert.ok(isBlockedAddress('fe90::1'));
  assert.ok(isBlockedAddress('febf::1'));
  // IPv4-mapped IPv6 (dotted notation)
  assert.ok(isBlockedAddress('::ffff:127.0.0.1'));
  // IPv4-mapped IPv6 (hex notation)
  assert.ok(isBlockedAddress('::ffff:7f00:1'));
  // Case insensitivity
  assert.ok(isBlockedAddress('FD00::1'));
  // IPv4 range boundaries
  assert.ok(!isBlockedAddress('172.15.255.255'));
  assert.ok(isBlockedAddress('172.16.0.0'));
  assert.ok(isBlockedAddress('172.31.255.255'));
  assert.ok(!isBlockedAddress('172.32.0.0'));
  assert.ok(!isBlockedAddress('100.63.255.255'));
  assert.ok(isBlockedAddress('100.64.0.0'));
  assert.ok(isBlockedAddress('100.127.255.255'));
  assert.ok(!isBlockedAddress('100.128.0.0'));
  // fe80::/10 boundaries
  assert.ok(!isBlockedAddress('fec0::1'));
  // Public addresses
  assert.ok(!isBlockedAddress('1.1.1.1'));
  assert.ok(!isBlockedAddress('140.82.112.3'));
  assert.ok(!isBlockedAddress('2606:4700::1'));
});

test('refuses allowlisted hostname that resolves to loopback', async () => {
  const logs: Record<string, unknown>[] = [];
  const proxy = createProxy({ allow: parseAllow('localhost:9999'), log: (o) => logs.push(o) });
  const port = await listen(proxy);
  try {
    const { sock, head } = await rawRequest(port, 'CONNECT localhost:9999 HTTP/1.1\r\nHost: localhost:9999\r\n\r\n');
    assert.match(head, /^HTTP\/1\.1 403/);
    sock.destroy();
    assert.ok(logs.some((l) => l.event === 'refused' && l.reason === 'private address'));
  } finally {
    proxy.close();
  }
});

test('survives repeated refused CONNECT with immediate reset', async () => {
  const echo = createServer((s) => s.pipe(s));
  const echoPort = await listen(echo);
  try {
    const proxy = createProxy({ allow: parseAllow(`api.anthropic.com,127.0.0.1:${echoPort}`), log: () => {} });
    const port = await listen(proxy);
    try {
      // Send multiple refused CONNECTs with immediate socket destruction
      for (let i = 0; i < 5; i++) {
        const { sock } = await rawRequest(port, 'CONNECT evil.example.com:443 HTTP/1.1\r\nHost: evil.example.com:443\r\n\r\n');
        sock.destroy();
      }
      // Verify the proxy is still alive and can handle an allowed connection
      const { sock, head } = await rawRequest(port, `CONNECT 127.0.0.1:${echoPort} HTTP/1.1\r\nHost: 127.0.0.1:${echoPort}\r\n\r\n`);
      assert.match(head, /^HTTP\/1\.1 200/);
      sock.destroy();
    } finally {
      proxy.close();
    }
  } finally {
    echo.close();
  }
});

test('upstream close after 200 does not send 502', async () => {
  // Create a server that accepts connections and sends TCP RST
  // Wait for the first client byte so the reset always hits an established tunnel.
  const destroyer = createServer((s) => s.once('data', () => s.resetAndDestroy()));
  const destroyerPort = await listen(destroyer);
  try {
    const proxy = createProxy({ allow: parseAllow(`127.0.0.1:${destroyerPort}`), log: () => {} });
    const proxyPort = await listen(proxy);
    try {
      const { sock, head } = await rawRequest(proxyPort, `CONNECT 127.0.0.1:${destroyerPort} HTTP/1.1\r\nHost: 127.0.0.1:${destroyerPort}\r\n\r\n`);
      assert.match(head, /^HTTP\/1\.1 200/);
      // Collect all bytes received, including the initial 200
      let allData = head;
      const remaining = await new Promise((r) => {
        const timer = setTimeout(() => r(''), 100);
        sock.on('data', (d) => {
          allData += d;
        });
        sock.write('x');
        sock.on('close', () => {
          clearTimeout(timer);
          r('');
        });
      });
      // Should not contain a 502 error response anywhere
      assert.ok(!allData.includes('502'), `Should not have 502 anywhere in response, got: ${allData}`);
      sock.destroy();
    } finally {
      proxy.close();
    }
  } finally {
    destroyer.close();
  }
});

const untilZeroConnections = async (server: Server) => {
  for (let i = 0; i < 200; i++) {
    const n = await new Promise<number>((r, j) => server.getConnections((e, c) => (e ? j(e) : r(c))));
    if (n === 0) return;
    await new Promise((r) => setImmediate(r));
  }
  throw new Error('proxy connections never reached 0');
};

const deferred = <T = void>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
};

test('client close during DNS lookup never dials upstream', async () => {
  const lookupCalled = deferred();
  const lookupResult = deferred<{ address: string; family: number }[]>();
  let connectCalls = 0;
  const proxy = createProxy({
    allow: parseAllow('stall.example:443'),
    log: () => {},
    lookup: () => { lookupCalled.resolve(); return lookupResult.promise; },
    connect: () => { connectCalls++; throw new Error('connect must not be called'); },
  });
  const port = await listen(proxy);
  try {
    const sock = connect(port, '127.0.0.1', () => sock.write('CONNECT stall.example:443 HTTP/1.1\r\nHost: stall.example:443\r\n\r\n'));
    sock.on('error', () => {});
    await lookupCalled.promise;
    sock.resetAndDestroy(); // RST: the proxy socket is allowHalfOpen, so a bare FIN would not close it
    await untilZeroConnections(proxy);
    lookupResult.resolve([{ address: '1.1.1.1', family: 4 }]);
    for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r));
    assert.equal(connectCalls, 0);
  } finally {
    proxy.close();
  }
});

test('client close before upstream connect destroys upstream', async () => {
  const connectCalled = deferred();
  const destroyed = deferred();
  // Just what the proxy touches on an upstream socket.
  const fake = new EventEmitter() as EventEmitter & { destroyed: boolean; destroy(): void; setTimeout(): void; write(): void; pipe(): void };
  fake.destroyed = false;
  fake.destroy = () => { fake.destroyed = true; destroyed.resolve(); };
  fake.setTimeout = () => {};
  fake.write = () => {};
  fake.pipe = () => {};
  const proxy = createProxy({
    allow: parseAllow('203.0.113.5:443'),
    log: () => {},
    connect: () => { connectCalled.resolve(); return fake as unknown as Socket; },
  });
  const port = await listen(proxy);
  let timer: NodeJS.Timeout | undefined;
  try {
    const sock = connect(port, '127.0.0.1', () => sock.write('CONNECT 203.0.113.5:443 HTTP/1.1\r\nHost: 203.0.113.5:443\r\n\r\n'));
    sock.on('error', () => {});
    await connectCalled.promise;
    sock.resetAndDestroy(); // RST: see note in the DNS-guard test
    const timeout = new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('upstream was not destroyed after client close')), 1000); });
    await Promise.race([destroyed.promise, timeout]);
    assert.equal(fake.destroyed, true);
  } finally {
    clearTimeout(timer);
    proxy.close();
  }
});

test('listens on a Unix socket, replacing a stale one, and tunnels CONNECT through it', async () => {
  const { statSync, rmSync } = await import('node:fs');
  const { join } = await import('node:path');
  const { listenOn } = await import('../proxy.ts');
  const dir = tmp('p-');
  const sockPath = join(dir, 'proxy.sock');
  // A stale socket left by a proxy process that died without cleaning up.
  const { spawnSync } = await import('node:child_process');
  const { lstatSync } = await import('node:fs');
  spawnSync(process.execPath, ['-e', `require('node:net').createServer().listen(${JSON.stringify(sockPath)}, () => process.kill(process.pid, 'SIGKILL'))`]);
  assert.ok(lstatSync(sockPath).isSocket(), 'the stale socket exists');

  const echo = createServer((s) => s.pipe(s));
  const echoPort = await listen(echo);
  const proxy = createProxy({ allow: parseAllow(`127.0.0.1:${echoPort}`), log: () => {} });
  try {
    const where = await listenOn(proxy, sockPath);
    assert.equal(where, sockPath);
    assert.equal(statSync(sockPath).mode & 0o777, 0o600);
    const sock = connect(sockPath);
    const head = await new Promise<string>((resolve, reject) => {
      let data = '';
      sock.on('connect', () => sock.write(`CONNECT 127.0.0.1:${echoPort} HTTP/1.1\r\n\r\n`));
      sock.on('data', (d) => { data += d; if (data.includes('\r\n\r\n')) resolve(data); });
      sock.on('error', reject);
    });
    assert.match(head, /^HTTP\/1\.1 200/);
    const echoed = await new Promise((r) => { sock.once('data', (d) => r(String(d))); sock.write('ping'); });
    assert.equal(echoed, 'ping');
    sock.destroy();
  } finally {
    proxy.close();
    echo.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test('refuses to replace a socket path that is not a socket', async () => {
  const { writeFileSync, readFileSync, rmSync } = await import('node:fs');
  const { join } = await import('node:path');
  const { listenOn } = await import('../proxy.ts');
  const dir = tmp('p-');
  const p = join(dir, 'proxy.sock');
  writeFileSync(p, 'not a socket');
  const proxy = createProxy({ allow: parseAllow(''), log: () => {} });
  try {
    await assert.rejects(listenOn(proxy, p), /not a socket/);
    assert.equal(readFileSync(p, 'utf8'), 'not a socket');
  } finally {
    proxy.close();
    rmSync(dir, { recursive: true, force: true });
  }
});

test('listenOn keeps TCP for a port or the default', async () => {
  const { listenOn } = await import('../proxy.ts');
  const proxy = createProxy({ allow: parseAllow(''), log: () => {} });
  try {
    const where = await listenOn(proxy, '0', '127.0.0.1');
    assert.equal(typeof where, 'number');
    assert.ok((where as number) > 0);
  } finally {
    proxy.close();
  }
});

test('the proxy process refuses to start without an absolute GROVE_LISTEN socket path', async () => {
  const { spawnSync } = await import('node:child_process');
  const { fileURLToPath } = await import('node:url');
  const main = fileURLToPath(new URL('../main.ts', import.meta.url));
  for (const value of [undefined, '', '3128', 'relative/proxy.sock']) {
    const env: NodeJS.ProcessEnv = { ...process.env, GROVE_ALLOW: 'example.com' };
    delete env.GROVE_LISTEN;
    if (value !== undefined) env.GROVE_LISTEN = value;
    const r = spawnSync(process.execPath, [main], { env, encoding: 'utf8', timeout: 10_000 });
    assert.notEqual(r.status, 0, `GROVE_LISTEN=${JSON.stringify(value)} must not start`);
    assert.match(r.stderr, /GROVE_LISTEN/);
  }
});
