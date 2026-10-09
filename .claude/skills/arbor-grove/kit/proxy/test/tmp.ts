// Every temporary directory a test makes lives under one root per test process. The root is
// removed when the process exits, and roots left behind by runs that were killed are swept the
// next time any test process starts, so a test run never leaves anything in the system temp dir.
// The root path stays short: some tests put Unix sockets in it (macOS caps those at 104 bytes).
import { mkdirSync, mkdtempSync, readdirSync, rmSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const BASE = join(tmpdir(), 'grove-t');
const STALE_MS = 6 * 60 * 60 * 1000;

const alive = (pid: number) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return (e as NodeJS.ErrnoException).code === 'EPERM';
  }
};

mkdirSync(BASE, { recursive: true });
for (const name of readdirSync(BASE)) {
  const pid = Number(/^(\d+)-/.exec(name)?.[1]);
  const path = join(BASE, name);
  let old = false;
  try {
    old = Date.now() - statSync(path).mtimeMs > STALE_MS;
  } catch {
    continue;
  }
  if (pid && alive(pid) && !old) continue;
  rmSync(path, { recursive: true, force: true });
}

const ROOT = mkdtempSync(join(BASE, `${process.pid}-`));
// Code under test that makes its own scratch directories (git worktrees, bundles, judge runs)
// and the processes it spawns use os.tmpdir(), so point that inside the root as well.
process.env.TMPDIR = ROOT;

export function cleanupTmp() {
  try {
    rmSync(ROOT, { recursive: true, force: true, maxRetries: 3 });
  } catch {
    // Best effort: the next test process sweeps whatever is left.
  }
}

process.on('exit', cleanupTmp);
for (const [signal, code] of [['SIGINT', 130], ['SIGTERM', 143], ['SIGHUP', 129]] as const) {
  process.once(signal, () => {
    cleanupTmp();
    process.exit(code);
  });
}

export const tmp = (prefix = 't-') => mkdtempSync(join(ROOT, prefix));
