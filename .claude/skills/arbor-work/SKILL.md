---
name: arbor-work
description: Run the mandatory agentic work cycle for a slice of work — assign a work ID, branch, author and apply an OpenSpec change, gate on the project's verification command, archive, commit, push, and integrate. Use when starting or completing any non-trivial change. Defaults to autonomous; pass --interaction to run with approval prompts.
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
  `main` at the end.
- **interactive** (`--interaction`): ask for approval before applying and before
  archiving; open a pull request at the end instead of merging.

## Inputs

A short description of the slice of work, and optionally the type (`DEV` for
development — the default — or `INFRA` for infrastructure) and mode.

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
7. **Archive.** Interactive: ask for approval. Then invoke
   `openspec-archive-change` to move the change to `openspec/changes/archive/`.
8. **Commit** with a subject `{ticket}: {short description}` (uppercase work ID,
   e.g. `DEV-4: add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented.
9. **Push** the branch.
10. **Integrate.** Autonomous: merge to `main`. Interactive: open a pull request.

## Guardrails

- Never skip step 6 when a gate exists. A failing gate stops the cycle.
- One change = one work ID = one branch. Keep them in sync.
