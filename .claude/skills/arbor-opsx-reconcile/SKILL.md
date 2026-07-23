---
name: arbor-opsx-reconcile
description: Use when code changes exist on a branch that were made outside the openspec lifecycle - without a proposal, design, or tasks. Reconciles the diff so every change maps to an openspec change that can be archived correctly.
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: arbor
  version: "1.0"
---

Reconcile code changes with the openspec lifecycle. Ensures every diff on the current branch is covered by a change with complete artifacts, ready to archive.

---

## Goal

Any code change done outside the normal openspec flow (propose → apply → archive) should, after reconciliation, look as if it was properly proposed and implemented. The output is one or more openspec changes with all artifacts present and all tasks marked complete — ready to archive.

---

## Steps

### 1. Get the branch diff

```bash
git diff $(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/main")...HEAD --stat
```

If `@{u}` fails (no upstream), fall back to `origin/main`. Show the summary to the user so they know what's being reconciled.

If the diff is empty, tell the user there's nothing to reconcile and stop.

### 2. List existing openspec changes

```bash
openspec list --json
```

For each active change, read its artifacts to understand what it covers:
- `openspec/changes/<name>/proposal.md` — the "what & why"
- `openspec/changes/<name>/tasks.md` — the task list (check for unchecked `- [ ]` items)
- Any specs at `openspec/changes/<name>/specs/`

**Goal:** Build a mental map of `{ change-name → files/features covered }`.

### 3. Identify uncovered changes

Get the full diff to analyze content:

```bash
git diff $(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "origin/main")...HEAD
```

Compare each changed file/feature against the existing change map from step 2.

Classify each changed file as:
- **Covered** — clearly part of an existing active change
- **Partially covered** — loosely related but not explicitly listed in tasks
- **Uncovered** — no change exists for it

If everything is covered and all change tasks are complete, inform the user and stop.

### 4. Group uncovered changes into logical proposals

Group uncovered files by feature/concern — don't create one change per file. Use judgment:
- Related files that implement the same feature → one change
- Infrastructure/config changes → one change
- Refactors → one change
- Each group gets a kebab-case name derived from its purpose

Show the user the groupings and ask for confirmation before creating anything:

> "I found N uncovered areas. I'll create these changes: [list]. Proceed?"

Use **AskUserQuestion tool** if groupings are unclear.

### 5. Create retroactive changes and artifacts

For each group, create the change and generate retroactive artifacts.

#### Create the change

```bash
openspec new change "<name>"
```

#### Get artifact build order

```bash
openspec status --change "<name>" --json
```

#### Create artifacts using openspec instructions

For each artifact in dependency order:

```bash
openspec instructions <artifact-id> --change "<name>" --json
```

Follow the instructions, using the actual diff as the source of truth for content:
- `proposal.md` — describe what was built and why (infer from the diff)
- `design.md` — describe how it was implemented (infer from the code changes)
- `tasks.md` — list the implementation steps as tasks, **all marked `[x]`** since they are already done

**Critical:** When writing `tasks.md`, every task must be `- [x]` (complete). These are retroactive — the work is already done.

Continue until all `applyRequires` artifacts are complete (per `openspec status --json`).

### 6. Handle partially-covered changes

For changes that are **partially covered** (files loosely related to an existing change):

- Read the existing change's `tasks.md`
- Determine if the uncovered files represent work that should be added as completed tasks
- If yes: append `- [x]` tasks to the existing `tasks.md`
- If the existing change's scope is too narrow, consider a separate change instead

### 7. Verify coverage

After creating all retroactive changes, confirm coverage:

```bash
openspec list --json
```

Summarize:
- Which changes were found already covering diffs
- Which new changes were created
- Whether any diffs remain unaccounted for (and why, if intentional)

---

## Output

```
## Reconciliation Complete

**Branch diff:** N files changed

**Existing coverage:**
- ✓ <change-name>: covers <files/features>

**Created retroactive changes:**
- ✓ <change-name>: <what it covers> (N tasks, all complete)
- ✓ <change-name>: <what it covers> (N tasks, all complete)

**Ready to archive:** Run /openspec-archive-change for each change above.
```

---

## Guardrails

- Never create one change per file — group by logical concern
- All tasks in retroactive changes must be `[x]` (already done)
- Always confirm groupings with the user before creating changes
- Use `openspec instructions` for artifact guidance — don't freehand the structure
- If a file's purpose is genuinely unclear, ask the user rather than guessing
- Don't modify existing change artifacts unless the user explicitly agrees
- If uncovered changes are trivial (e.g., `.gitignore` tweaks), ask if the user wants to group them or skip
