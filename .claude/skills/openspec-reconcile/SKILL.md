---
name: openspec-reconcile
description: Reconcile the current git diff with OpenSpec documentation. Ensures all code changes have corresponding OpenSpec artifacts (proposal, design, specs, tasks) as if they were planned from the start.
license: MIT
compatibility: Requires openspec CLI and git.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.3.1"
---

Reconcile code changes with OpenSpec documentation — ensure every change in the git diff is reflected in OpenSpec artifacts.

**Input**: Optionally specify a git ref to diff against (default: `HEAD`). Optionally specify a change name to update. If omitted, a new change is created or an existing one is selected.

**Steps**

1. **Get the current diff**

   ```bash
   git diff --stat
   git diff --name-only
   ```

   Then read the full diff for context:
   ```bash
   git diff
   ```

   If the working tree is clean, try staged changes:
   ```bash
   git diff --cached --name-only
   ```

   If both are clean, try diffing against the merge base:
   ```bash
   git diff main...HEAD --name-only
   ```

   **IMPORTANT**: Exclude all files under `openspec/` and any `.kiro/` paths from analysis. These are documentation files — never document documentation.

2. **Analyze the changes**

   From the diff, identify:
   - What features/behaviors were added
   - What was modified or refactored
   - What was removed
   - Group related file changes into logical units of work

   Ignore:
   - Files under `openspec/` (change artifacts themselves)
   - Files under `.kiro/` (skills/prompts)
   - Auto-generated files (lock files, build outputs) unless they reflect meaningful dependency changes

3. **Check existing OpenSpec documentation**

   ```bash
   openspec list --json
   ```

   Read existing change artifacts to determine what's already documented. Compare the diff analysis against documented changes to find gaps.

4. **Determine the reconciliation strategy**

   - **If an active change exists that covers some of the diff**: modify it to cover all changes
   - **If no relevant change exists**: create a new one
   - **If changes span multiple unrelated features**: create separate changes for each logical group

   If ambiguous, use the **AskUserQuestion tool** to ask:
   > "I see changes spanning multiple areas: [list]. Should I create one change covering everything, or separate changes? If one, what should it be called?"

5. **Create or update OpenSpec artifacts**

   For each change being documented:

   a. **If creating new**: 
      ```bash
      openspec new change "<name>"
      ```

   b. **Get artifact instructions and create/update each**:
      ```bash
      openspec status --change "<name>" --json
      openspec instructions <artifact-id> --change "<name>" --json
      ```

   c. **Write artifacts based on the actual code changes**:
      - **proposal.md**: Describe what was built and why, derived from the diff
      - **design.md**: Document the technical approach actually taken (architecture, patterns, data flow)
      - **specs.md**: Capture the behavioral requirements the code satisfies
      - **tasks.md**: List all implementation steps as completed (`[x]`) since the work is done

   d. **All artifacts should read as if written before implementation** — forward-looking language ("will", "should"), not past-tense ("was added", "we changed")

6. **Mark all tasks complete**

   Since the code already exists, every task in tasks.md should be `[x]`. The task list should represent the logical steps someone would follow to implement these changes from scratch.

7. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

```
## Reconciliation Complete

### Changes Documented
- **<change-name>**: <brief description>
  - proposal.md — <summary>
  - design.md — <summary>
  - specs.md — <summary>
  - tasks.md — N tasks (all complete)

### Files Covered
- <list of files from diff now documented>

### Files Excluded
- <any openspec/ or .kiro/ files skipped>

All code changes are now reflected in OpenSpec documentation.
```

**Artifact Writing Guidelines**

- Write as if planning the work, not describing what happened
- Use present/future tense: "The system provides..." not "We added..."
- Derive requirements from actual code behavior — read the implementation to understand what it does
- Design docs should reflect the architecture as-built
- Tasks should be ordered logically (dependencies first) and all marked complete
- Follow the `template` and `instruction` from `openspec instructions` for structure

**Guardrails**
- NEVER include `openspec/` files in the analysis or documentation
- NEVER include `.kiro/` files in the analysis or documentation
- NEVER create recursive documentation (documenting the act of documenting)
- All tasks must be marked `[x]` since the code already exists
- If the diff is empty, inform the user and exit — don't create empty documentation
- If changes are trivial (typo fixes, formatting), ask if documentation is really needed
- Prefer updating an existing active change over creating a new one when the changes are related
- Read the actual code (not just the diff) when you need more context to write accurate specs
