---
description: Implement a task end-to-end — propose a change, implement all tasks, reconcile, test, commit, and push
---

Implement a task end-to-end: propose → apply → commit.

**Input**: `/opsx:implement [TICKET] [description]`
- `TICKET` — optional ticket number (e.g. `ABC-123`), passed through to commit
- `description` — optional change description; if omitted, the propose step will ask

**Steps**

1. **Propose**

   Use `openspec-propose` to create the change and all artifacts.
   Pass the description (if provided). Wait for all artifacts to be created before continuing.
   Note the change name for step 2.

2. **Apply**

   Use `openspec-apply-change` with the change name from step 1.
   Implement all tasks until complete or a blocker is hit.
   If blocked: surface the issue to the user and stop — do not proceed to commit.

3. **Commit**

   Use `openspec-commit`, passing `TICKET` if provided.
   Runs reconcile → stages all files → runs tests → generates commit message → commits → pushes.
   Stop if tests fail or reconcile has unresolvable gaps.

**Guardrails**
- Never skip propose — implementation must have a documented change
- Never commit if apply was paused due to a blocker
- Never commit if tests fail
