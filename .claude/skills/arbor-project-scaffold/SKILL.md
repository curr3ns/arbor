---
name: arbor-project-scaffold
description: Use when starting a brand-new project — an empty or nearly-empty directory that needs to become a working repo. Interrogates the user, then scaffolds structure, testing, Docker profiles, an optional local reverse proxy, the docs/roadmaps/ layout the rest of the loop reads, OpenSpec, quality rules, the gate, VCS, and CI/CD, and hands off to arbor-auto-roadmap for planning. Stack-agnostic.
license: MIT
metadata:
  author: arbor
  version: "1.3"
---

# Arbor scaffold

Turn an empty directory into a project with the arbor house practices baked in:
`packages/` subdivision, OpenSpec + the `/arbor-auto-work` cycle, a real verification
gate, two Docker profiles on a claimed port block, local proxy hostnames when
a reverse proxy is available, VCS and CI/CD wiring, and
quality rules for both agents and humans. Stack-agnostic: interrogate first,
derive specifics per stack.

**Generate nothing until the recap in step 8 is approved.** Interrogation uses
one topic per question (AskUserQuestion where multiple-choice fits) and
continues until you are confident the plan satisfies every requirement.

**Scaffold, don't build.** Everything generated proves the stack is wired —
it compiles, it runs, its one smoke test passes, its pipeline goes green — it
never proves the product works. Real features are backlog items worked
through `/arbor-auto-work` after this skill hands off; none get built here,
no matter how small or tempting "just to prove it works."

## Steps

You MUST create a todo per step and complete them in order.

### Phase 1 — Interrogate

1. **Preflight, then what is being built.** First verify the environment the
   later steps depend on — `docker info` and `openspec --version` both
   succeed; the directory contains nothing beyond dotfiles/README — and stop
   with a clear message if not. Then interrogate: domain, kind of application
   (web app, API, CLI, library, pipeline…), and stack, down to the choices the
   scaffold needs (framework, package/dependency manager, language version).
   Nothing is assumed; if the answer is a TypeScript monorepo, default to pnpm
   workspaces.
2. **Name.** Skip if the directory name is already the intended name and the
   user confirms it. Otherwise ask whether to use the tree theme this time
   (arbor, alder, banyan, maple…); either way suggest candidates that resonate
   with the description and don't collide with sibling directories in the
   projects root.
3. **Structure.** Propose a package subdivision that fits the stack and kind —
   e.g. `packages/{backend,frontend,shared,database,e2e}` — with one clear
   purpose and one-way dependencies per package. Scale the count to the
   project (a small one may need only two or three packages) but keep the
   `packages/` layout and the one-purpose boundaries. Confirm or edit with the
   user.
4. **Ports.** Scan sibling projects for claimed port blocks:
   ```bash
   grep -rhoE '9[0-9]{3}' ../*/docker-compose*.yml ../*/deployment/*.yml \
     ../*/.env* ../*/config ../*/CLAUDE.md ../*/README.md 2>/dev/null | sort -u
   ```
   Every hit claims its whole hundred (9213 claims 9200–9299). Propose the
   hundred above the highest claimed block (9200, 9300 claimed → propose
   9400) — default profile `9x00–9x09`, e2e/agent profile `9x10–9x19` — and
   ask the user to confirm or override.
5. **Testing strategy.** Propose stack-appropriate tools honoring these
   invariants: unit tests live beside source in each package; integration/e2e
   tests run against the Docker e2e profile, never the default ports; coverage
   is gated at 100% with only narrow, named exclusions — the stack's analog of
   type-only files and thin live-wiring modules (`*.runtime.ts` in TS,
   `__main__.py` in Python). If the project has a database, use versioned
   migrations with flyway-style names (`V<n>__description.sql`) run by Flyway
   in compose unless the stack has an established equivalent, plus a
   name-check script wired into the gate.
6. **VCS.** Git is the VCS, always. Ask which host, if any: GitHub, GitLab,
   Bitbucket, or local-only (no remote). If a host is chosen, ask visibility
   (public/private), whether to create and push the remote now, the default
   branch name (default `main`), and whether it should be branch-protected —
   require a check to pass before merge — which ties to the CI/CD choice
   next. "No remote" is a valid answer; it must be chosen, not assumed.
7. **CI/CD.** Ask whether to wire up a pipeline. If yes, default to the
   chosen VCS host's native CI (GitHub Actions for GitHub, GitLab CI for
   GitLab; ask explicitly for Bitbucket or local-only) and confirm: it
   triggers on push and PR to the default branch, and its only job is to run
   the gate — nothing bespoke. Confirm whether it should be the required
   check behind the branch protection from step 6. "No CI/CD" is a valid
   answer; it must be chosen, not assumed.
8. **Recap.** Restate every decision — stack, name, packages, ports, testing,
   VCS, CI/CD, what Docker runs — and get an explicit go before touching any
   file.

### Phase 2 — Generate

9. **Scaffold** in the current directory: workspace manifest, the agreed
   packages, and minimal source that compiles, runs, and has at least one
   test per package proving the wiring — a health check, a smoke test, a
   hello-world route — never coverage fillers, and never a real feature.
   Anything resembling product/business logic belongs to the first
   `/arbor-auto-work` cycle, not the scaffold.
10. **Docker.** One `docker-compose.yml` at the root with host ports as
    `${VAR:-default}` and per-profile env files (local vs e2e/agent) wired to
    the claimed block. Healthchecks on every service. Stack scripts:
    `stack:up`/`stack:down` and `stack:e2e:up`/`stack:e2e:down` (or the
    stack's equivalent). If the app can't be fully containerized,
    containerize at least its dependencies (db, brokers) and document what
    runs on the host.
11. **Reverse proxy.** Only if one is available: `nginx -v` succeeds and an
    infrastructure root is discoverable and writable without `sudo`. Find it
    by reading the `include` lines in `nginx.conf` and taking the directory
    they glob over, resolving symlinks; `~/Infrastructure/nginx` is the usual
    answer, with `/opt/homebrew/etc/nginx` and `/etc/nginx` as fallbacks on
    an unconfigured machine. If either check fails, skip the whole step and
    say so in the step 20 hand-off; the project is fully usable on raw ports,
    so a missing proxy is a skipped convenience, never a failure.

    The root is organised project-first, one directory per project holding
    everything that project owns:

    ```
    <infra>/<name>.local/servers/   vhost files
    <infra>/<name>.local/ssl/       certificate.conf, local.crt, local.key
    <infra>/<name>.local/logs/      access and error logs
    <infra>/ssl-generate.sh         shared cert reissue script
    ```

    A project is therefore one self-contained directory — movable, archivable,
    and deletable on its own. That shape requires `nginx.conf` to glob across
    projects rather than down from a single servers directory:

    ```
    http   { include <infra>/*/servers/*; }
    stream { include <infra>/*/stream/*; }
    ```

    Check those includes already cover the new project — the glob usually
    means they do — and if `nginx.conf` still points somewhere else, print the
    line to add rather than editing it silently. Write every path in a
    generated config as the resolved absolute location, never through the
    package manager's prefix, so the configs survive a Homebrew move or a
    different distribution's layout.

    For each compose service that serves HTTP on a claimed host port, derive a
    subdomain from its package name (`backend`→`api`, `frontend`→`www`,
    otherwise the package name) and write one vhost per profile under
    `<infra>/<name>.local/servers/`:

    | Profile | Hostname | Upstream |
    |---|---|---|
    | default | `<sub>.<name>.local` | `127.0.0.1:9x0n` |
    | e2e/agent | `<sub>.e2e.<name>.local` | `127.0.0.1:9x1n` |

    Services that don't speak HTTP — databases, brokers, caches — get no
    vhost; reach them on their port. Each vhost follows the house template:
    `:80` returning `301` to https; `:443 ssl` with the project wildcard cert;
    access and error logs at
    `<infra>/<name>.local/logs/<logbase>.{access,error}.log` where `logbase` is
    `<sub>` or `<sub>.e2e` — create that directory, because nginx fails its
    own config test when a log directory is missing; the standard proxy header
    and timeout block; and `proxy_pass http://127.0.0.1:<port>/` — always the
    literal IP, never `localhost`, which resolves to `::1` first on macOS.
    Also write `<infra>/<name>.local/ssl/certificate.conf` with both SANs, since
    `*.<name>.local` is single-level and does not cover the dotted e2e names:

    ```
    [alt_names]
    DNS.1   = *.<name>.local
    DNS.2   = *.e2e.<name>.local
    ```

    The reissue script is shared across projects, not per-project. If
    `<infra>/ssl-generate.sh` is missing — likely on a machine that has never
    hosted one of these projects — write it: it runs `openssl req -x509
    -nodes -days 3650 -newkey rsa:4096` under `sudo` against the project's
    `certificate.conf`, then hands the results back with `chown` to the user
    nginx runs as and sets the key to `600` and the cert to `644`. That chown
    is load-bearing, not hygiene: `openssl` ran as root and leaves a
    world-readable key behind, but nginx runs as the logged-in user on a
    Homebrew install, so a `600` root-owned key is unreadable and nginx will
    refuse to start. Lock the key down and hand it over in the same step, or
    not at all.

    Then emit, never execute, the steps that need `sudo`: write
    `/tmp/<name>-hosts.txt` with a `127.0.0.1 <host>` line per hostname
    (comment out any already present in `/etc/hosts`), and print a checklist
    covering the `/etc/hosts` append, `../../ssl-generate.sh certificate.conf`
    run from `<infra>/<name>.local/ssl`, the Keychain import-and-trust, and
    `nginx -t && nginx -s reload`. Run `nginx -t` yourself to prove the
    generated config parses, reload if the master process runs as the current
    user, and confirm each hostname actually routes with
    `curl -k --resolve <host>:443:127.0.0.1 https://<host>/`. That bypasses
    `/etc/hosts`, so it works before the user has appended anything, and any
    HTTP status — `502` included, when the stack isn't up — proves nginx is
    answering for that name. Never invoke `sudo`, never edit `/etc/hosts`,
    and never generate a certificate — those are the user's to run.
12. **Roadmaps.** Create `docs/roadmaps/` and `docs/roadmaps/archive/`, each
    holding a `.gitkeep` so both survive the initial commit while empty. This
    is the layout the rest of the loop expects: `arbor-auto-roadmap` writes
    plans to `docs/roadmaps/<slug>.md`, `arbor-auto-developer` reads that
    directory as its work queue, and `arbor-auto-work` migrates a roadmap into
    `archive/` once its last item is checked. Create the directories only —
    never author a roadmap file, a phase, or an item here. What the project
    should build is the user's to plan, and scaffolding a placeholder roadmap
    would put words in their mouth.
13. **OpenSpec.** Run `openspec init`, then write `openspec/config.yaml`:
    `schema: spec-driven`; a `context` block covering what the project is,
    stack, structure, conventions, the work-ID/branch/commit process, and the
    two-profile port rule; `rules` for proposal/specs/tasks (SHALL/MUST +
    WHEN/THEN scenarios, grouped small verifiable tasks).
14. **Quality rules.** `CLAUDE.md` golden rules: agents use the e2e profile
    only (name the ports, and the `<sub>.e2e.<name>.local` URLs when step 11
    created them); all non-trivial work goes through
    `/arbor-auto-work`; the gate is real — name the command; CI/CD runs the
    same gate on every push/PR (name the pipeline, or note there isn't one);
    honor the conventions. Plus a commands table. `docs/CONVENTIONS.md`:
    narrow drill-down directories, concise self-documenting files, reuse over
    duplication, extension over redefinition, simplest solution, tests beside
    source, file/migration naming, and the coverage exclusion policy.
15. **Gate.** A single command (`gate` script or stack equivalent) chaining
    lint, typecheck (or stack analog), the migration name-check when one
    exists, coverage-gated tests, build, and e2e-in-Docker (bring the e2e
    stack up, run, tear down). This is the command `/arbor-auto-work` step 6
    will run, and the command CI/CD calls in step 16.
16. **CI/CD.** If step 7 confirmed a pipeline, generate its config
    (`.github/workflows/gate.yml`, `.gitlab-ci.yml`, or the chosen host's
    equivalent): triggers on push and PR to the default branch, checks out
    the repo, installs dependencies, then runs the exact gate command from
    step 15 — no duplicated or bespoke steps. Skip this step only if the user
    explicitly declined CI/CD in step 7; the recap record notes the decision
    either way.
17. **VCS.** `git init` (skip if already a repo); `.gitignore` covering IDE
    files (`.idea/`, `*.iml`, `.vscode/`), OS noise (`.DS_Store`), local env
    files, dependencies, and build/coverage output. If step 6 asked for a
    remote, create it now with the host's CLI (`gh repo create`,
    `glab repo create`, …) at the agreed visibility and default branch name —
    if the CLI is missing or unauthenticated, stop and tell the user rather
    than silently skipping. Apply the branch protection requested in step 6
    once both the remote and the CI/CD check from step 16 exist.

### Phase 3 — Verify and record

18. **Run the gate end-to-end.** It MUST pass on the fresh scaffold. Fix
    until it does; do not proceed otherwise.
19. **Record the bootstrap.** Author an `INFRA-1-scaffold` OpenSpec change
    documenting the structure and archive it immediately — note in it that
    the scaffold was bootstrapped by hand because the cycle it defines did
    not yet exist. Commit everything with subject `INFRA-1 scaffold <name>`,
    and push to the remote if step 17 created one — this is the commit the
    CI/CD pipeline from step 16 should turn green on.
20. **Hand off to planning.** Close by naming `arbor-auto-roadmap` as the
    natural next step: the scaffold is a working repo with no plan in it, and
    that skill is what interrogates the user into one, writing it to the
    `docs/roadmaps/` directory step 12 created. From there `arbor-auto-developer`
    burns the roadmap down one item at a time. Name it and stop — do not invoke
    it, and do not start planning here; it is human-invoked, and this skill's
    job is finished.

## Guardrails

- No generated files before the step 8 go — interrogation first, always. The
  user's opening message never counts as recap approval.
- Scaffolding only, no features. Minimal source proves the stack is wired —
  it doesn't implement product behavior. "Just this one small thing to prove
  it works" is still out of scope; a health check or smoke test already
  proves the wiring. The first feature is the first `/arbor-auto-work` cycle,
  never something built by hand during scaffolding.
- VCS and CI/CD are interrogated, never assumed. A "local-only" or "no
  CI/CD" answer is fine, but it must be an explicit answer the user gave, not
  a default the agent picked to save a question.
- The gate passes only when every stage passes, including e2e-in-Docker.
  "Passes except the Docker part" is a failing gate; a failing gate stops the
  scaffold — never hand over a project whose own gate fails.
- Two profiles, one port block: never put e2e on the default ports.
- The reverse proxy is convenience, never a dependency. Compose, the gate, and
  the e2e suite address services as `127.0.0.1:<port>`, so a machine with no
  nginx — CI, a fresh laptop, a teammate — runs the identical gate. A test or
  script that only works through a `.local` hostname is a bug.
- The proxy step never runs `sudo`, never edits `/etc/hosts`, and never
  generates a certificate. It writes the files it owns and prints the rest;
  privileged changes are the user's to make.
- Minimal source ≠ empty source: everything scaffolded compiles, runs, and is
  tested for real.
