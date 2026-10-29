# Verification

How step 6 proves the change works. The project profile (see
`references/profile.md`) names the repo-specific commands, services, test-data
recipes and environments. This file holds the rules that apply everywhere.

## Every suite runs whole

Every test category runs its **entire** suite, not just the new or related
tests. Filtered runs (`--tests X`, a single spec file, a test-name argument)
never count, and neither does an `UP-TO-DATE` or cached task: use the build
tool's clean or rerun switch so tests really execute. Read the build file, the
repo's `CLAUDE.md`/`AGENTS.md` and the CI spec for the real tasks.

For any failure, decide whether the change caused it — re-run on a clean
checkout of the base branch when unsure. Fix regressions. A test that is
broken before the change too is listed explicitly, with that proof, in
`hiccups` and `followups`. A broken test anywhere in a changed repo fails the
cycle until it is fixed or proven pre-existing.

### Unit and integration: fast stage, then slow stage

1. **Fast stage:** the repo's normal full build the way CI's build step runs it
   (e.g. `./gradlew clean build`, or a full `npm test` plus `npm run build`).
   Fix everything before moving on.
2. **Slow stage** (only once the fast stage passed): when the repo marks some
   specs slow and skips them in the normal build, run the repo's own task that
   enables them — never a hand-set environment variable that imitates it. Find
   it by grepping the build file and CI spec for `slow`, `sonar`, or similar;
   if none exists, say so in the report. Slow runs can take many minutes: run
   them in the background and wait on completion.

Unit and integration tests are **one** report row, `Unit`: record the fast
stage first, then replace it with the slow-stage totals once that passes (the
slow run is a superset), listing both commands in `command`, one per line. The
`summary` gives real totals and `BUILD SUCCESSFUL`; the exit code must be 0,
and the slow row's skipped count must not include the slow specs.

### Automation suite

When a changed repo has an end-to-end or API automation suite (e.g. a
`test-automation/` directory), the plan always adds a test there for the new or
changed behavior, following existing patterns. Then:

- **The new test always runs.** If something blocks it, fix the environment for
  the run (install dependencies, point the config at the local stack for the
  run and revert that before handoff, use test data you created). A `skipped`
  automation row is not acceptable; keep going until it passes or fails on a
  real product problem.
- **The full automation suite runs too** — every existing spec that applies to
  the changed repo, not a single file — against the local stack. Record it as a
  separate row (`Automation (full suite)`) with pass/fail/skipped counts.
- **No new scripts.** Add the spec (and, only if truly needed, a small reusable
  helper that follows existing patterns), never a new npm script, runner
  script, or one-off CLI for a single ticket. Run the spec through the existing
  generic scripts.

## Verify the behavior every way that applies

Run all of these that apply, and record which ran:

1. **Unit tests** — always.
2. **Integration tests** — where the repo has them.
3. **Automation tests** — where the repo has a suite, as above.
4. **In-browser verification with Claude in Chrome** — for anything with a UI,
   including backend changes whose output a UI shows. Load the
   `claude-in-chrome` skill first, drive the real app on the local stack, walk
   the acceptance criteria, and save screenshots as evidence. For changes with
   no UI path, verify through the API (`curl` with a real token) instead.

Compare the results against the acceptance criteria.

**Never skip browser verification because the stack isn't running.** A service
that is not started is a task, not a reason to skip:

1. Start what is missing, using the profile's recipes (proxy config, services,
   IDE run configurations — prefer those through the IDE's MCP tools when
   available, else background shells).
2. Build the test data the scenario needs, log in, and walk the criteria.
3. If something fails to start, diagnose and fix it (ports, env vars, missing
   config, a dependency not built) and retry; spend real effort before giving
   up, and fix local setup problems rather than routing around them.
4. Only if it is still impossible after genuine attempts, or the change truly
   has no UI path, record the Browser row as `skipped` with **what you tried and
   the exact blocker**, add it to `hiccups` and `followups`, and verify through
   the API instead. A bare "not started" is not an acceptable reason.

Record anything new learned about starting the stack where the profile says
lessons go.

## Test data

Build every scenario from fresh data you create for this cycle. Never reuse a
specific account or record quoted in the ticket (an id given as an example, an
account from another environment): such data may not exist locally, may sit
outside what the local stack loads, and is not yours to modify. Only modify
data you created. No direct database writes to set up state; use the product's
own tools and admin UIs. If a scenario cannot be built that way, stop and ask
(say what you tried) instead of falling back to existing data.

Never write passwords or live tokens into files, the report, or commits.
