import { test } from 'node:test';
import assert from 'node:assert/strict';
import { connect, createServer } from 'node:net';
import { existsSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmp } from './tmp.ts';
import { join } from 'node:path';
import { createRelay, startRelay } from '../relay.ts';
import type { AddressInfo, Server } from 'node:net';
import type { StartOptions } from '../relay.ts';

const listenTcp = (server: Server) => new Promise<number>((r) => server.listen(0, '127.0.0.1', () => r((server.address() as AddressInfo).port)));
const listenUnix = (server: Server, path: string) => new Promise<void>((r) => server.listen(path, r));
const close = (server: Server) => new Promise<void>((r) => server.close(() => r()));

function roundTrip(port: number, text: string) {
  return new Promise<string>((resolve, reject) => {
    const sock = connect(port, '127.0.0.1', () => sock.write(text));
    let data = '';
    sock.on('data', (d) => {
      data += d;
      if (data.length >= text.length) {
        sock.destroy();
        resolve(data);
      }
    });
    sock.on('close', () => resolve(data));
    sock.on('error', reject);
  });
}

test('a TCP client reaches a Unix-socket server through the relay', async () => {
  const dir = tmp('r-');
  const socketPath = join(dir, 'proxy.sock');
  const echo = createServer((s) => s.pipe(s));
  await listenUnix(echo, socketPath);
  const relay = createRelay({ socketPath, log: () => {} });
  const port = await listenTcp(relay);
  try {
    assert.equal(await roundTrip(port, 'hello through the relay'), 'hello through the relay');
    assert.equal(await roundTrip(port, 'and again'), 'and again');
  } finally {
    await close(relay);
    await close(echo);
    rmSync(dir, { recursive: true, force: true });
  }
});

test('a missing socket closes the client and the relay keeps serving', async () => {
  const dir = tmp('r-');
  const socketPath = join(dir, 'proxy.sock');
  const logs: Record<string, unknown>[] = [];
  const relay = createRelay({ socketPath, retryMs: 300, retryIntervalMs: 50, log: (o) => logs.push(o) });
  const port = await listenTcp(relay);
  try {
    assert.equal(await roundTrip(port, 'nobody home'), '');
    assert.ok(logs.some((l) => l.event === 'upstream-error'));
    // The socket appears later: the same relay now works.
    const echo = createServer((s) => s.pipe(s));
    await listenUnix(echo, socketPath);
    assert.equal(await roundTrip(port, 'now it works'), 'now it works');
    await close(echo);
  } finally {
    await close(relay);
    rmSync(dir, { recursive: true, force: true });
  }
});

test('retries while the socket is not there yet', async () => {
  const dir = tmp('r-');
  const socketPath = join(dir, 'proxy.sock');
  const relay = createRelay({ socketPath, retryMs: 3000, retryIntervalMs: 50, log: () => {} });
  const port = await listenTcp(relay);
  const echo = createServer((s) => s.pipe(s));
  try {
    const pending = roundTrip(port, 'early bird');
    setTimeout(() => listenUnix(echo, socketPath), 300);
    assert.equal(await pending, 'early bird');
  } finally {
    await close(relay);
    await close(echo);
    rmSync(dir, { recursive: true, force: true });
  }
});

test('an upstream reset does not crash the relay', async () => {
  const dir = tmp('r-');
  const socketPath = join(dir, 'proxy.sock');
  const rude = createServer((s) => s.destroy());
  await listenUnix(rude, socketPath);
  const relay = createRelay({ socketPath, log: () => {} });
  const port = await listenTcp(relay);
  try {
    for (let i = 0; i < 5; i++) await roundTrip(port, 'x').catch(() => {});
    assert.ok(relay.listening);
  } finally {
    await close(relay);
    await close(rude);
    rmSync(dir, { recursive: true, force: true });
  }
});

// A fatal relay start: the callback gets the exit code instead of the process exiting.
const started = (opts: Omit<StartOptions, 'onReady' | 'exit'>) => new Promise<{ relay: Server; code: number | null }>((resolve) => {
  const relay = startRelay({ ...opts, onReady: () => resolve({ relay, code: null }), exit: (code) => resolve({ relay, code }) });
});

test('the relay aborts with exit 3 and writes no marker when its port is already taken (review I1)', async () => {
  const dir = tmp('r-');
  const squatter = createServer(() => {});
  const port = await listenTcp(squatter);
  const readyPath = join(dir, 'grove-relay.ready');
  try {
    const { relay, code } = await started({ socketPath: join(dir, 'proxy.sock'), port, readyPath, log: () => {} });
    assert.equal(code, 3);
    assert.equal(existsSync(readyPath), false, 'no readiness marker after a failed listen');
    assert.equal(relay.listening, false);
  } finally {
    await close(squatter);
  }
});

test('the relay writes its pid to a private readiness marker only once it is listening (review I1)', async () => {
  const dir = tmp('r-');
  const readyPath = join(dir, 'grove-relay.ready');
  const { relay, code } = await started({ socketPath: join(dir, 'proxy.sock'), port: 0, readyPath, log: () => {} });
  try {
    assert.equal(code, null);
    assert.equal(relay.listening, true);
    assert.equal(readFileSync(readyPath, 'utf8'), String(process.pid));
    assert.equal(statSync(readyPath).mode & 0o777, 0o600);
  } finally {
    await close(relay);
  }
});

test('the relay refuses a readiness marker that already exists (review I1)', async () => {
  const dir = tmp('r-');
  const readyPath = join(dir, 'grove-relay.ready');
  writeFileSync(readyPath, '1');
  const { relay, code } = await started({ socketPath: join(dir, 'proxy.sock'), port: 0, readyPath, log: () => {} });
  assert.equal(code, 1);
  assert.equal(readFileSync(readyPath, 'utf8'), '1');
  assert.equal(relay.listening, false, 'the relay closed again');
});
