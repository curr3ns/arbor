---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work — assign a work ID, branch, author and apply an OpenSpec change, gate on the project's verification command, archive, commit, push, and integrate. Use when starting or completing any non-trivial change. Defaults to autonomous; pass --interaction to run with approval prompts, or --pr to run autonomously but open a pull request instead of merging.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor work cycle

The required process for all non-trivial work in a repo. It layers the
work-ID + branch conventions on top of the OpenSpec propose/apply/archive
skills. Two modes:

- **autonomous** (default): proceed through every step without prompts; merge to
  `main` at the end. Pass `--pr` to end by pushing and opening a pull request
  instead of merging — still no prompts.
- **interactive** (`--interaction`): ask for approval before applying and before
  archiving; open a pull request at the end instead of merging.

## Inputs

A short description of the slice of work, and optionally the type (`DEV` for
development — the default — or `INFRA` for infrastructure) and mode
(`--interaction` or `--pr`).

## Steps

You MUST create a todo per step and complete them in order.

1. **Determine the slice.** Restate the smallest shippable unit of work. If it's
   too big for one change, stop and split it.
2. **Assign the work ID.** Type is an **uppercase** `DEV` (default), `INFRA`, or
   another established uppercase type. The next number is one more than the
   highest existing ID of that type across `openspec/changes/` and
   `openspec/changes/archive/`:
   ```bash
   ls -d openspec/changes/*/ openspec/changes/archive/*/ 2>/dev/null \
     | grep -oE '[A-Z]+-[0-9]+' | sort -t- -k2 -n
   ```
   Form the change name `<TYPE>-<n>-<slug>`: uppercase type prefix, lowercase
   kebab-case slug (e.g. `DEV-4-add-cart`). The change name **is** the work ID.
3. **Create the branch** `feature|bugfix|hotfix/<id>-<slug>` (feature for
   features, bugfix for fixes, hotfix for hotfixes), e.g.
   `feature/DEV-4-add-cart`.
4. **Author the proposal.** Invoke the `openspec-propose` skill with the work
   description to generate proposal, design, specs, and tasks under the change.
5. **Apply.** Interactive: ask for approval, then implement. Autonomous: invoke
   `openspec-apply-change` / implement directly. Follow the repo's conventions if
   present (`CLAUDE.md`, `docs/CONVENTIONS.md`): narrow directories, concise
   files, reuse, extension, tests beside source.
6. **Run the gate.** If the project defines a verification command — an
   `npm run gate` / test / lint / build script, or a gate documented in the
   repo — run it. It MUST pass end-to-end; do not proceed otherwise. If the repo
   defines no such command, note that and continue.

   Some gates distinguish a stage's outcome into more than plain pass/fail —
   e.g. an e2e/integration stage that can report the environment itself was
   unreachable (no daemon, registry egress blocked, stack never came up)
   separately from the suite actually running and failing. When the gate
   makes that distinction, handle the three outcomes differently:
   - **Passed for real:** proceed exactly as normal; no note needed.
   - **Environment-blocked** (the stage never actually ran against real
     infrastructure): the cycle MAY proceed to commit/archive/integrate, but
     the commit message — and the PR/merge note, if one is opened — MUST
     include a visible note that this stage was not verified and why. Never
     merge this silently as if it were a full pass.
   - **Genuine failure** (the stage ran and failed): a real implementation
     problem, never reclassified as environment-blocked — stop the cycle like
     any other gate failure below.
   If the gate makes no such distinction, a pass is a pass and a failure
   stops the cycle, per the paragraph above.
7. **Archive.** Interactive: ask for approval. Then invoke
   `openspec-archive-change` to move the change to `openspec/changes/archive/`.
8. **Commit** with a subject `{ticket} {short description}` (uppercase work ID,
   e.g. `DEV-4 add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented. If step 6
   reported an environment-blocked stage, add a bullet surfacing it, e.g.
   `- E2E skipped: environment-blocked (<reason>); not independently
   verified.`
9. **Push** the branch.
10. **Integrate.** Autonomous: merge to `main` — unless `--pr` was passed, in
    which case push and open a pull request instead of merging. Interactive: open
    a pull request.

## Guardrails

- Never skip step 6 when a gate exists. A failing gate stops the cycle.
- A gate stage may only be treated as skipped when it itself reports an
  environment-blocked outcome — never as a shortcut, and never for a genuine
  failure against infrastructure that did come up. A skipped stage must
  always leave a visible trace (commit bullet, and PR/merge note if
  applicable) — never merge unverified changes silently.
- One change = one work ID = one branch. Keep them in sync.
