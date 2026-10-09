// The agent container runs with network none (spec §6.4). This relay is its only way
// out: it listens on 127.0.0.1:3128, where HTTP(S)_PROXY points, and pipes each
// connection to the egress proxy's Unix socket on the per-agent sock volume.
// No dependencies; a socket error only ever ends that one connection.
import { connect, createServer } from 'node:net';
import type { Server, Socket } from 'node:net';
import { closeSync, openSync, realpathSync, writeSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const RETRYABLE = new Set<string | undefined>(['ENOENT', 'ECONNREFUSED']);

export type RelayLog = (o: Record<string, unknown>) => unknown;
export interface RelayOptions { socketPath: string; retryMs?: number; retryIntervalMs?: number; log?: RelayLog }
export interface StartOptions {
  socketPath: string;
  port?: number;
  host?: string;
  readyPath: string;
  onReady?: () => unknown;
  exit?: (code: number) => unknown;
  log?: RelayLog;
}

export function createRelay({
  socketPath,
  retryMs = 5000, // the egress may still be starting: keep trying this long per connection
  retryIntervalMs = 100,
  log = (o) => process.stderr.write(`${JSON.stringify({ relay: true, ...o })}\n`),
}: RelayOptions): Server {
  return createServer((client) => {
    client.pause();
    const deadline = Date.now() + retryMs;
    let upstream: Socket | null = null;
    let timer: NodeJS.Timeout | undefined;
    const destroyBoth = () => {
      clearTimeout(timer);
      client.destroy();
      upstream?.destroy();
    };
    client.on('error', destroyBoth);
    client.on('close', destroyBoth);

    const attempt = () => {
      if (client.destroyed) return;
      let connected = false;
      const u = connect(socketPath);
      upstream = u;
      u.on('connect', () => {
        connected = true;
        client.pipe(u);
        u.pipe(client);
        client.resume();
      });
      u.on('error', (e: NodeJS.ErrnoException) => {
        if (!connected && RETRYABLE.has(e.code) && Date.now() < deadline && !client.destroyed) {
          u.destroy();
          timer = setTimeout(attempt, retryIntervalMs);
          return;
        }
        log({ event: 'upstream-error', error: e.code ?? e.message });
        destroyBoth();
      });
      u.on('close', () => {
        if (connected) destroyBoth();
      });
    };
    attempt();
  });
}

// Serves host:port and, only once listening, writes this process's pid to readyPath (created
// exclusively, mode 600, on the agent's own tmpfs). The entrypoint runs the driver only after
// it sees that marker with the relay's pid, so a service in the agent's pod that took the port
// first can never stand in for the relay (review I1). There is no fallback: a port already in
// use exits 3, any other failure exits 1.
export function startRelay({
  socketPath, port = 3128, host = '127.0.0.1', readyPath,
  onReady = () => {},
  exit = (code) => process.exit(code),
  log = (o) => process.stderr.write(`${JSON.stringify({ relay: true, ...o })}\n`),
}: StartOptions): Server {
  const relay = createRelay({ socketPath, log });
  relay.on('error', (e: NodeJS.ErrnoException) => {
    log({ event: 'listen-failed', error: e.code ?? e.message });
    exit(e.code === 'EADDRINUSE' ? 3 : 1);
  });
  relay.listen(port, host, () => {
    try {
      const fd = openSync(readyPath, 'wx', 0o600);
      try {
        writeSync(fd, String(process.pid));
      } finally {
        closeSync(fd);
      }
    } catch (e) {
      log({ event: 'ready-marker-failed', error: (e as NodeJS.ErrnoException).code ?? (e as Error).message });
      relay.close();
      exit(1);
      return;
    }
    onReady();
  });
  return relay;
}

// Run directly (from the entrypoint).
const isMain = (() => {
  try {
    return process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
})();

if (isMain) {
  startRelay({
    socketPath: process.env.GROVE_EGRESS_SOCKET || '/run/grove-egress/proxy.sock',
    port: Number(process.env.GROVE_RELAY_PORT || 3128),
    readyPath: process.env.GROVE_RELAY_READY || '/tmp/grove-relay.ready',
  });
}
