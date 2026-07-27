---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work — assign a work ID, branch, author and apply an OpenSpec change, gate on the project's verification command, archive, commit, push, and integrate. Use when starting or completing any non-trivial change. Accepts spec:/work:/gate:/archive: model tokens and forwards them to the lifecycle. Defaults to autonomous; pass --interaction to run with approval prompts, or --pr to run autonomously but open a pull request instead of merging.
license: MIT
metadata:
  author: arbor
  version: "1.1"
---

# Arbor work cycle

The required process for all non-trivial work in a repo. It layers the
work-ID + branch conventions and the commit/push/integrate steps on top of the
`arbor-opsx-auto` OpenSpec lifecycle (propose → apply → gate → archive). Two
modes:

- **autonomous** (default): proceed through every step without prompts; merge to
  `main` at the end. Pass `--pr` to end by pushing and opening a pull request
  instead of merging — still no prompts.
- **interactive** (`--interaction`): ask for approval before applying and before
  archiving (both handled inside the lifecycle); open a pull request at the end
  instead of merging.

## Inputs

A short description of the slice of work, and optionally the type (`DEV` for
development — the default — or `INFRA` for infrastructure), mode (`--interaction`
or `--pr`), and per-phase model tokens (`spec:`/`work:`/`gate:`/`archive:`, bare
or behind `--models`). The model tokens are not interpreted here — they are
stripped from the description and forwarded to `arbor-opsx-auto`, which owns the
model defaults and parsing (see its **Model selection** section).

## Steps

You MUST create a todo per step and complete them in order.

0. **Split off model tokens.** Set aside any `spec:`/`work:`/`gate:`/`archive:`
   tokens (bare or behind `--models`) and the `--interaction`/`--pr` flags. What
   remains is the work description used everywhere below. Keeping the model
   tokens out now ensures they never leak into the work-ID slug in steps 2–3.

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
4. **Run the OpenSpec lifecycle.** Invoke the `arbor-opsx-auto` skill with the
   slice as the work description, the `<TYPE>-<n>-<slug>` change name from step 2,
   and the model tokens set aside in step 0 forwarded verbatim. In
   `--interaction` mode, pass `--interaction` so it asks for approval before apply
   and before archive. It proposes, applies, runs the project's gate, and
   archives the change on the current branch under the requested (or default)
   per-phase models, leaving everything uncommitted. **Read back its reported gate
   outcome** — in particular an environment-blocked stage and its reason, which
   step 5 must surface. A genuine gate failure or any incomplete task stops the
   lifecycle there; do not continue to commit.
5. **Commit** with a subject `{ticket} {short description}` (uppercase work ID,
   e.g. `DEV-4 add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented. If step 4
   reported an environment-blocked stage, add a bullet surfacing it, e.g.
   `- E2E skipped: environment-blocked (<reason>); not independently
   verified.`
6. **Push** the branch.
7. **Integrate.** Autonomous: merge to `main` — unless `--pr` was passed, in
   which case push and open a pull request instead of merging. Interactive: open
   a pull request.

## Guardrails

- The gate runs inside `arbor-opsx-auto` (step 4); a genuine gate failure stops
  the cycle there and you never reach commit.
- A gate stage may only be treated as skipped when it itself reports an
  environment-blocked outcome — never as a shortcut, and never for a genuine
  failure against infrastructure that did come up. When step 4 reports one, that
  skipped stage MUST leave a visible trace here (commit bullet, and PR/merge note
  if applicable) — never merge unverified changes silently.
- One change = one work ID = one branch. Keep them in sync.
