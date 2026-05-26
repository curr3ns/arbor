---
name: openspec-implement
description: Use when the user wants to implement a task end-to-end: propose a change, implement it, and commit. Accepts an optional ticket number and optional change description.
---

# openspec-implement

Implement a task end-to-end: propose → apply → commit.

**Announce at start:** "Using openspec-implement for end-to-end implementation."

## Input

`/opsx:implement [TICKET] [description]`

- `TICKET` — optional ticket number (e.g. `ABC-123`), passed through to commit
- `description` — optional change description; if omitted, `opsx:propose` will ask

## Steps

### 1. Propose

**REQUIRED SUB-SKILL:** Use `openspec-propose` to create the change and all artifacts.

- Pass the description (if provided) as input to propose
- Wait for propose to complete — all artifacts must exist before continuing
- Note the change name for use in step 2

### 2. Apply

**REQUIRED SUB-SKILL:** Use `openspec-apply-change` to implement all tasks in the change.

- Use the change name from step 1
- Continue until all tasks are marked `[x]` or a blocker requires user input
- If paused due to a blocker: surface the issue to the user and **stop** — do not proceed to commit

### 3. Commit

**REQUIRED SUB-SKILL:** Use `openspec-commit` with `TICKET` (if set).

- Runs reconcile, stages all files, runs tests, generates commit message, commits and pushes
- Stop if tests fail or reconcile finds unresolvable gaps

## Guardrails

- Never skip propose — implementation must have a documented change
- Never commit if apply was paused due to a blocker
- Never commit if tests fail
