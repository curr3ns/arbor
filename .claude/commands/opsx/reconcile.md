---
name: "OPSX: Reconcile"
description: Reconcile git diff with OpenSpec documentation — ensure all code changes have corresponding artifacts as if they were planned from the start
category: Workflow
tags: [workflow, artifacts, experimental]
---

Reconcile code changes with OpenSpec documentation — ensure every change in the git diff is reflected in OpenSpec artifacts.

**Input**: Optionally specify a git ref to diff against (e.g., `/opsx:reconcile main`). Default: diff working tree or staged changes.

**Steps**

1. **Get the current diff**

   ```bash
   git diff --stat
   git diff --name-only
   ```

   Then read the full diff:
   ```bash
   git diff
   ```

   If clean, try staged (`git diff --cached`) or branch diff (`git diff main...HEAD`).

   **IMPORTANT**: Exclude all `openspec/` and `.kiro/` paths. Never document documentation.

2. **Analyze the changes**

   Identify features/behaviors added, modified, or removed. Group related file changes into logical units. Ignore `openspec/`, `.kiro/`, lock files, and build outputs.

3. **Check existing OpenSpec documentation**

   ```bash
   openspec list --json
   ```

   Compare diff against documented changes to find gaps.

4. **Determine reconciliation strategy**

   - If an active change covers some of the diff: modify it to cover all
   - If no relevant change exists: create a new one
   - If changes span unrelated features: ask whether to create one or multiple changes

5. **Create or update artifacts**

   For each change:
   ```bash
   openspec new change "<name>"
   openspec status --change "<name>" --json
   openspec instructions <artifact-id> --change "<name>" --json
   ```

   Write artifacts based on actual code:
   - **proposal.md**: What and why
   - **design.md**: Technical approach taken
   - **specs.md**: Behavioral requirements satisfied
   - **tasks.md**: Implementation steps, all marked `[x]`

   Write in forward-looking language as if planning, not past-tense.

6. **Mark all tasks complete** — code already exists, all tasks are `[x]`

7. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

```
## Reconciliation Complete

### Changes Documented
- **<change-name>**: <brief description>
  - proposal.md, design.md, specs.md, tasks.md

### Files Covered
- <files from diff now documented>

All code changes are now reflected in OpenSpec documentation.
```

**Guardrails**
- NEVER include `openspec/` or `.kiro/` files in analysis or documentation
- NEVER create recursive documentation
- All tasks must be `[x]` since code already exists
- If diff is empty, inform user and exit
- If changes are trivial, ask if documentation is needed
- Write as if planning, not describing history
- Read actual code for context when the diff alone is insufficient
