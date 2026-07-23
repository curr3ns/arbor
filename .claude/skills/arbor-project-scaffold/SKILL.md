---
name: arbor-project-scaffold
description: Use when starting a brand-new project — an empty or nearly-empty directory that needs to become a working repo. Interrogates the user, then scaffolds structure, testing, Docker profiles, OpenSpec, quality rules, the gate, and git. Stack-agnostic.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor scaffold

Turn an empty directory into a project with the arbor house practices baked in:
`packages/` subdivision, OpenSpec + the `/arbor-auto-work` cycle, a real verification
gate, two Docker profiles on a claimed port block, and quality rules for both
agents and humans. Stack-agnostic: interrogate first, derive specifics per
stack.

**Generate nothing until the recap in step 6 is approved.** Interrogation uses
one topic per question (AskUserQuestion where multiple-choice fits) and
continues until you are confident the plan satisfies every requirement.

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
6. **Recap.** Restate every decision — stack, name, packages, ports, testing,
   what Docker runs — and get an explicit go before touching any file.

### Phase 2 — Generate

7. **Scaffold** in the current directory: workspace manifest, the agreed
   packages, and minimal source that compiles, runs, and has at least one
   meaningful test per package — never coverage fillers.
8. **Docker.** One `docker-compose.yml` at the root with host ports as
   `${VAR:-default}` and per-profile env files (local vs e2e/agent) wired to
   the claimed block. Healthchecks on every service. Stack scripts:
   `stack:up`/`stack:down` and `stack:e2e:up`/`stack:e2e:down` (or the stack's
   equivalent). If the app can't be fully containerized, containerize at least
   its dependencies (db, brokers) and document what runs on the host.
9. **OpenSpec.** Run `openspec init`, then write `openspec/config.yaml`:
   `schema: spec-driven`; a `context` block covering what the project is,
   stack, structure, conventions, the work-ID/branch/commit process, and the
   two-profile port rule; `rules` for proposal/specs/tasks (SHALL/MUST +
   WHEN/THEN scenarios, grouped small verifiable tasks).
10. **Quality rules.** `CLAUDE.md` golden rules: agents use the e2e profile
    only (name the ports); all non-trivial work goes through `/arbor-auto-work`;
    the gate is real — name the command; honor the conventions. Plus a
    commands table. `docs/CONVENTIONS.md`: narrow drill-down directories,
    concise self-documenting files, reuse over duplication, extension over
    redefinition, simplest solution, tests beside source, file/migration
    naming, and the coverage exclusion policy.
11. **Gate.** A single command (`gate` script or stack equivalent) chaining
    lint, typecheck (or stack analog), the migration name-check when one
    exists, coverage-gated tests, build, and e2e-in-Docker (bring the e2e
    stack up, run, tear down). This is the command `/arbor-auto-work` step 6 will
    run.
12. **Git.** `git init` (skip if already a repo); `.gitignore` covering IDE
    files (`.idea/`, `*.iml`, `.vscode/`), OS noise (`.DS_Store`), local env
    files, dependencies, and build/coverage output.

### Phase 3 — Verify and record

13. **Run the gate end-to-end.** It MUST pass on the fresh scaffold. Fix until
    it does; do not proceed otherwise.
14. **Record the bootstrap.** Author an `INFRA-1-scaffold` OpenSpec change
    documenting the structure and archive it immediately — note in it that the
    scaffold was bootstrapped by hand because the cycle it defines did not yet
    exist. Commit everything with subject `INFRA-1 scaffold <name>`.

## Guardrails

- No generated files before the step 6 go — interrogation first, always. The
  user's opening message never counts as recap approval.
- The gate passes only when every stage passes, including e2e-in-Docker.
  "Passes except the Docker part" is a failing gate; a failing gate stops the
  scaffold — never hand over a project whose own gate fails.
- Two profiles, one port block: never put e2e on the default ports.
- Minimal source ≠ empty source: everything scaffolded compiles, runs, and is
  tested for real.
