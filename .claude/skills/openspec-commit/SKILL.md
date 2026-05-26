---
name: openspec-commit
description: Use when the user wants to reconcile, test, and commit all current changes. Accepts an optional ticket number to prefix the commit message.
---

# openspec-commit

Reconcile changes with OpenSpec, stage all files, run tests, generate a commit message, commit, and push.

**Announce at start:** "Using openspec-commit to reconcile, test, and push changes."

## Steps

### 1. Parse ticket number (optional)

If the user provided an argument (e.g. `/opsx:commit ABC-123`), store it as `TICKET`. Otherwise `TICKET` is empty.

### 2. Reconcile with OpenSpec

**REQUIRED SUB-SKILL:** Use `openspec-reconcile` to ensure all non-openspec changes in the diff are reflected in OpenSpec artifacts.

- If reconcile finds undocumented changes it cannot resolve automatically, surface them to the user and **stop** — do not proceed until documentation is complete.

### 3. Stage all changed files

```bash
git add -A
```

### 4. Run the test suite

Detect and run the project's test command:
- If `package.json` has a `test` script → `npm test`
- If `pytest.ini`, `pyproject.toml`, or `setup.cfg` present → `pytest`
- If `Makefile` has a `test` target → `make test`
- If unsure, ask the user which command to run

**If tests fail:** report the failures and **stop** — do not commit.

### 5. Generate the commit message

**REQUIRED SUB-SKILL:** Use `gencommit` with `TICKET` (if set) to generate the commit message written to a tmp file.

### 6. Commit

```bash
git commit -F <tmp file from gencommit>
```

### 7. Push

```bash
git push
```

If the branch has no upstream yet:
```bash
git push -u origin HEAD
```

## Guardrails

- Never commit if tests fail
- Never commit if reconcile finds undocumented changes it can't resolve
- Never force-push
