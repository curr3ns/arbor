---
name: arbor-opsx-modify
description: Use when the user wants to implement a specific change and have it properly documented in the OpenSpec lifecycle in one step. Implements first, then retroactively creates or updates proposal, design, tasks, and specs so the change can be archived. Use when the user wants to move fast without a separate planning phase.
metadata:
  type: skill
---

Implement a change and retroactively create or update its OpenSpec documentation in one step. The output is a fully documented change — proposal, design, completed tasks, and specs — ready to archive.

**Announce at start:** "Using arbor-opsx-modify to implement and document the change."

---

## Workflow

```
prompt → check for existing change → implement → document → ready to archive
```

This is the **implement-first** path. The artifacts are written after the code, reflecting what was actually done rather than what was planned.

---

## Steps

### 1. Parse the prompt

Extract:
- `CHANGE_DESCRIPTION` — what the user wants changed (required)
- `CHANGE_NAME` — optional name of an existing OpenSpec change to update

### 2. Check for an existing change to update

```bash
openspec list --json
```

**If `CHANGE_NAME` was given:** look it up in the list. If not found, warn and offer to create a new change with that name.

**If no `CHANGE_NAME` was given and active changes exist:** use **AskUserQuestion tool** to ask:
> "Should I add this work to an existing change, or create a new one?"
> Options: [list of active changes] + "Create a new change"

**If no active changes exist:** proceed directly to creating a new one.

### 3. Create a new change (if needed)

Derive a kebab-case name from `CHANGE_DESCRIPTION` (e.g. "add retry logic to payment service" → `add-payment-retry-logic`).

```bash
openspec new change "<name>"
```

### 4. Implement the change

Implement `CHANGE_DESCRIPTION` in the codebase:
- Make the minimal set of changes required
- Follow existing patterns and conventions
- Do not over-engineer beyond what was asked

### 5. Build a summary of what was done

After implementing, note:
- Files modified/created/deleted
- Behavior changes introduced
- APIs, contracts, or interfaces affected
- Any decisions made during implementation

This summary drives the artifact content in the next step.

### 6. Create or update artifacts

Get artifact status:

```bash
openspec status --change "<name>" --json
```

For each artifact that is `ready`, get instructions and write it:

```bash
openspec instructions <artifact-id> --change "<name>" --json
```

Write artifacts in dependency order until all `applyRequires` artifacts are complete.

---

#### Writing retroactive artifacts

**`proposal.md`** — What was changed and why:
- Describe the change and its motivation in past tense
- Keep scope tight: what this change does, not what might come later

**`design.md`** — How it was implemented:
- Describe the actual approach taken (not a plan — a record)
- Include key decisions and trade-offs made during implementation

**`tasks.md`** — What was done:
- List each logical step of implementation as a task
- **Every task must be `- [x]`** — work is already complete

**`specs/<capability>/spec.md`** (or delta specs if the schema uses them):
- Capture any new or changed behavior, interfaces, or contracts
- Written as a living specification, not a narrative of what happened

---

#### Updating an existing change's artifacts

When adding to an existing change:
1. Read each existing artifact before writing
2. **Append** — do not overwrite:
   - Add new `- [x]` tasks to the task list rather than replacing it
   - Extend the proposal/design with a new section describing the additional work
   - Merge spec changes into the existing spec
3. Preserve anything already in the artifacts

### 7. Verify all tasks are complete

Read `tasks.md` and confirm every task is `- [x]`. If any `- [ ]` remain (e.g. from a pre-existing task list), flag them to the user — they may represent work not yet done.

### 8. Show final status

```bash
openspec status --change "<name>"
```

Print:
- Change name and location
- Artifacts created or updated
- Summary of code changes (files modified)
- Whether any pre-existing incomplete tasks were found
- Next step hint: "Run `/openspec-archive-change` to archive this change into main specs."

---

## Output

```
## Change Implemented and Documented

**Change:** <change-name>
**Mode:** created | updated

### Code changes
- Modified: <file>, <file>
- Created: <file>

### Artifacts
- ✓ proposal.md — <one-line summary>
- ✓ design.md — <one-line summary>
- ✓ tasks.md — N tasks, all complete
- ✓ specs/<capability>/spec.md — <one-line summary>

Ready to archive. Run `/openspec-archive-change` when done.
```

---

## Guardrails

- **Implement first, document after** — never skip implementation and only write docs
- **All tasks must be `[x]`** — this skill creates retroactive tasks, not plans
- **Artifacts describe what happened** — past tense for proposal/design, present tense for specs
- **Don't over-scope** — artifacts should cover exactly this change, not adjacent work
- **Updating an existing change:** always read first, then append — never clobber existing content
- **If the change description is ambiguous:** use **AskUserQuestion** to clarify before implementing
- **If implementation reveals the change is larger than described:** pause, inform the user, and confirm scope before continuing
- Use `openspec instructions` for artifact structure — don't freehand the format
