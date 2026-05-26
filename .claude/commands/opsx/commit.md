---
name: "OPSX: Commit"
description: Reconcile changes with OpenSpec, run tests, generate a commit message, commit, and push
category: Workflow
tags: [workflow, commit, experimental]
---

Reconcile, test, commit, and push all current changes.

**Input**: Optional ticket number (e.g. `/opsx:commit ABC-123`).

**Steps**

1. **Parse ticket number** — store as `TICKET` if provided.

2. **Reconcile with OpenSpec**

   Use `openspec-reconcile` to verify all non-openspec changes are reflected in OpenSpec artifacts. Stop if unresolvable gaps remain.

3. **Stage all files**

   ```bash
   git add -A
   ```

4. **Run tests**

   Detect test command:
   - `package.json` with `test` script → `npm test`
   - `pytest.ini` / `pyproject.toml` / `setup.cfg` → `pytest`
   - `Makefile` with `test` target → `make test`
   - Otherwise ask the user

   Stop if tests fail. Report failures clearly.

5. **Generate commit message**

   Use `gencommit` (passing `TICKET` if set) to write the message to a tmp file.

6. **Commit**

   ```bash
   git commit -F <tmp file>
   ```

7. **Push**

   ```bash
   git push
   ```

   If no upstream: `git push -u origin HEAD`

**Guardrails**
- Never commit if tests fail
- Never commit if reconcile has unresolved documentation gaps
- Never force-push
