import { createProxy, listenOn, parseAllow } from './proxy.ts';

// Spec §6.5: in production the proxy listens only on the Unix socket in the agent's
// sock volume. TCP stays available to tests through listenOn, never here.
const where = process.env.GROVE_LISTEN ?? '';
if (!where.startsWith('/')) {
  console.error(`grove-egress: GROVE_LISTEN must be an absolute Unix socket path, got ${JSON.stringify(where)}`);
  process.exit(2);
}

const allow = parseAllow(process.env.GROVE_ALLOW ?? '');
const proxy = createProxy({ allow });
await listenOn(proxy, where);
console.log(JSON.stringify({ event: 'listening', on: where, allow: [...allow] }));
