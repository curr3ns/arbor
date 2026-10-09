import { createServer } from 'node:http';
import { connect as netConnect, isIP } from 'node:net';
import { promises as dns } from 'node:dns';
import { lstat, unlink } from 'node:fs/promises';
import type { IncomingMessage, Server } from 'node:http';
import type { AddressInfo, Socket } from 'node:net';

export type ProxyLog = (o: Record<string, unknown>) => unknown;
export type Lookup = (host: string) => Promise<{ address: string }[]>;
export type Connect = (port: number, host: string, onConnect: () => void) => Socket;
export interface ProxyOptions { allow: Set<string>; log?: ProxyLog; lookup?: Lookup; connect?: Connect }

export function parseAllow(csv: string): Set<string> {
  return new Set(
    csv.split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
      .map((s) => (s.includes(':') ? s : `${s}:443`)),
  );
}

// Check if an IP address is in a blocked (private/reserved) range
export function isBlockedAddress(ip: string): boolean {
  ip = ip.toLowerCase();

  // IPv6 addresses
  if (ip.includes(':')) {
    // Check for hex IPv4-mapped IPv6 addresses (::ffff:7f00:1 format)
    if (ip.startsWith('::ffff:') && !ip.slice(7).includes('.')) {
      const hexPart = ip.slice(7);
      const parts = hexPart.split(':');
      if (parts.length >= 2) {
        try {
          const a = parseInt(parts[parts.length - 2], 16);
          const b = parseInt(parts[parts.length - 1], 16);
          const ipv4 = `${a >> 8}.${a & 0xff}.${b >> 8}.${b & 0xff}`;
          return isBlockedAddress(ipv4);
        } catch {
          return false;
        }
      }
    }
    // Check for dotted IPv4-mapped IPv6 addresses (::ffff:a.b.c.d format)
    if (ip.startsWith('::ffff:') && ip.slice(7).includes('.')) {
      const ipv4 = ip.slice(7);
      return isBlockedAddress(ipv4);
    }
    // ::, ::1, fc00::/7, fe80::/10
    if (ip === '::' || ip === '::1') return true;
    if (ip.startsWith('fc') || ip.startsWith('fd')) return true; // fc00::/7
    // fe80::/10 - check first hextet
    if (ip.startsWith('fe')) {
      const endIdx = ip.indexOf(':');
      if (endIdx > 0) {
        const firstHextet = ip.slice(0, endIdx);
        try {
          const h = parseInt(firstHextet, 16);
          if ((h & 0xffc0) === 0xfe80) return true;
        } catch {
          // Invalid hex
        }
      }
    }
    return false;
  }

  // IPv4 addresses
  const parts = ip.split('.');
  if (parts.length !== 4) return false;
  const nums = parts.map(p => parseInt(p, 10));
  if (nums.some(n => isNaN(n) || n < 0 || n > 255)) return false;

  // 0.0.0.0/8
  if (nums[0] === 0) return true;
  // 10.0.0.0/8
  if (nums[0] === 10) return true;
  // 100.64.0.0/10
  if (nums[0] === 100 && nums[1] >= 64 && nums[1] <= 127) return true;
  // 127.0.0.0/8
  if (nums[0] === 127) return true;
  // 169.254.0.0/16
  if (nums[0] === 169 && nums[1] === 254) return true;
  // 172.16.0.0/12
  if (nums[0] === 172 && nums[1] >= 16 && nums[1] <= 31) return true;
  // 192.168.0.0/16
  if (nums[0] === 192 && nums[1] === 168) return true;

  return false;
}

// Spec §6.5: hostname allowlist for one agent; CONNECT only, everything else refused and logged.
export function createProxy({
  allow,
  log = (o) => console.log(JSON.stringify(o)),
  lookup = (host) => dns.lookup(host, { all: true }),
  connect = netConnect,
}: ProxyOptions): Server {
  const server = createServer((req, res) => {
    log({ event: 'refused', reason: 'only CONNECT is supported', method: req.method, url: req.url });
    res.writeHead(405).end();
  });

  server.maxConnections = 256;

  server.on('connect', (req: IncomingMessage, client: Socket, head: Buffer) => {
    // Attach error listener immediately to prevent crashes on client reset
    client.on('error', () => client.destroy());

    const target = String(req.url).toLowerCase();
    const i = target.lastIndexOf(':');
    const host = target.slice(0, i);
    const port = Number(target.slice(i + 1));
    if (i <= 0 || !port || !allow.has(target)) {
      log({ event: 'refused', target });
      client.end('HTTP/1.1 403 Forbidden\r\n\r\n');
      return;
    }

    // Check if host is a literal IP or needs DNS resolution
    if (isIP(host)) {
      // Literal IP: was configured explicitly in allowlist, connect directly
      connectUpstream(host);
    } else {
      // Hostname: resolve and check all addresses
      lookup(host)
        .then((addresses) => {
          // Return early if client was destroyed during DNS lookup
          if (client.destroyed) return;
          const blocked = addresses.some(a => isBlockedAddress(a.address));
          if (blocked) {
            log({ event: 'refused', target, reason: 'private address' });
            client.end('HTTP/1.1 403 Forbidden\r\n\r\n');
            return;
          }
          connectUpstream(addresses[0].address);
        })
        .catch((e) => {
          log({ event: 'refused', target, reason: 'dns-error', error: e.message });
          client.end('HTTP/1.1 502 Bad Gateway\r\n\r\n');
        });
    }

    function connectUpstream(resolvedHost: string) {
      let established = false;
      const upstream = connect(port, resolvedHost, () => {
        established = true;
        log({ event: 'allowed', target });
        client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        if (head?.length) upstream.write(head);
        upstream.pipe(client);
        client.pipe(upstream);
      });

      // 10 second connect timeout
      let connectTimeout = setTimeout(() => {
        log({ event: 'upstream-error', target, error: 'connect timeout' });
        client.end('HTTP/1.1 504 Gateway Timeout\r\n\r\n');
        upstream.destroy();
      }, 10000);

      upstream.on('connect', () => clearTimeout(connectTimeout));

      // 10 minute idle timeout using socket.setTimeout
      client.setTimeout(600000, () => {
        log({ event: 'idle-timeout', target });
        client.destroy();
        upstream.destroy();
      });
      upstream.setTimeout(600000, () => {
        log({ event: 'idle-timeout', target });
        client.destroy();
        upstream.destroy();
      });

      // Destroy both sides when either closes
      client.on('close', () => {
        clearTimeout(connectTimeout);
        // Always destroy upstream if it exists and isn't already destroyed
        if (!upstream.destroyed) upstream.destroy();
      });
      upstream.on('close', () => {
        clearTimeout(connectTimeout);
        if (established && !client.destroyed) client.destroy();
      });

      upstream.on('error', (e) => {
        clearTimeout(connectTimeout);
        log({ event: 'upstream-error', target, error: e.message });
        if (established) {
          // After 200 is sent, destroy the client
          client.destroy();
        } else {
          // Before 200 is sent, send error response first then destroy upstream
          client.end('HTTP/1.1 502 Bad Gateway\r\n\r\n');
          upstream.destroy();
        }
      });
    }
  });

  return server;
}

// Listens on a Unix socket when `where` is an absolute path (spec §6.5: the agent reaches
// the proxy only through its sock volume; the only mode main.js allows), else on a TCP
// port (default 3128; tests only). A stale socket from a previous run is replaced; any
// other file at the path is left alone.
// Resolves to the socket path or the bound port.
export async function listenOn(server: Server, where?: string | number, host = '0.0.0.0'): Promise<string | number> {
  const listen = (...args: [path: string] | [port: number, host: string]) => new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    // A path, or a port and host: the overloads cannot take the union, so it is spread as one shape.
    server.listen(...(args as [number, string]), () => {
      server.off('error', reject);
      resolve();
    });
  });

  if (typeof where === 'string' && where.startsWith('/')) {
    try {
      if (!(await lstat(where)).isSocket()) throw new Error(`${where} exists and is not a socket`);
      await unlink(where);
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code !== 'ENOENT') throw e;
    }
    // Created 0600 by the umask: no chmod by path afterwards, which a symlink swap could redirect.
    const previous = process.umask(0o177);
    try {
      await listen(where);
    } finally {
      process.umask(previous);
    }
    return where;
  }
  const port = where === undefined || where === '' ? 3128 : Number(where);
  if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error(`invalid listen address ${JSON.stringify(where)}`);
  await listen(port, host);
  return (server.address() as AddressInfo).port;
}
