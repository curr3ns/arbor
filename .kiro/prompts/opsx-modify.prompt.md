---
description: Modify an existing OpenSpec change with new behavior, updating all artifacts as if the change was always part of the plan
---

Modify an existing OpenSpec change - update artifacts to incorporate new behavior as if it were part of the original request, then generate new tasks for the delta.

**Input**: The argument after `/opsx:modify` is the modification description. Optionally prefix with a change name (e.g., `/opsx:modify add-auth also support OAuth2 providers`). If no change name, infer from context or prompt.

**Steps**

1. **Select the change to modify**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Modifying change: <name>"

2. **If no modification described, ask what to change**

   Use the **AskUserQuestion tool** (open-ended, no preset options) to ask:
   > "What behavior do you want to add or change in this feature?"

   **IMPORTANT**: Do NOT proceed without a clear modification request.

3. **Read current artifacts**

   ```bash
   openspec status --change "<name>" --json
   ```

   Read all existing artifact files (proposal, design, specs, tasks) from the change directory to understand the current state.

4. **Rewrite artifacts to incorporate the modification**

   Update each artifact so the new behavior reads as if it were part of the original request — not as an amendment or addendum.

   For each artifact that needs changes:

   a. **Get instructions for the artifact type**:
      ```bash
      openspec instructions <artifact-id> --change "<name>" --json
      ```
      Use the `template`, `instruction`, `context`, and `rules` to guide your rewrite.

   b. **Rewrite the artifact**:
      - Integrate the new behavior naturally into the existing content
      - Remove or update any content that conflicts with the modification
      - Maintain the same structure and style as the original
      - The result should read as a cohesive document, not a patched one

   c. **Order of updates**: proposal → design → specs → tasks
      (Follow dependency order from the schema)

5. **Generate new tasks for the modification**

   When updating tasks.md:
   - Mark previously completed tasks that are still valid as `[x]`
   - Mark previously completed tasks that need rework due to the modification as `[ ]` with a note
   - Add new `[ ]` tasks for the new behavior
   - Remove tasks that are no longer relevant
   - Ensure task ordering respects dependencies
   - New/reworked tasks should be implementable by `/opsx:apply`

6. **Show final status**
   ```bash
   openspec status --change "<name>"
   ```

**Output**

After modifying all artifacts, summarize:

```
## Change Modified: <change-name>

### What Changed
- <brief description of the modification>

### Artifacts Updated
- proposal.md — <what was added/changed>
- design.md — <what was added/changed>
- specs.md — <what was added/changed>
- tasks.md — <N new/reworked tasks added>

### Task Summary
- Previously completed: N tasks (still valid)
- Reworked (needs re-implementation): M tasks
- New tasks: P tasks
- Total remaining: M+P tasks

Ready for implementation. Run `/opsx:apply` to implement the changes.
```

**Guardrails**
- Always read ALL existing artifacts before making changes
- Rewrite artifacts holistically — the result must read as if the modification was always part of the plan
- Do NOT append "Amendment" or "Update" sections — integrate naturally
- Preserve completed task status for work that remains valid
- If the modification contradicts existing design decisions, resolve the conflict in favor of the modification and note what changed
- If the modification is unclear or could be interpreted multiple ways, ask for clarification
- Keep the same artifact structure and style as the originals
- Ensure new tasks are specific enough for `/opsx:apply` to implement without ambiguity
- If no artifacts exist yet, suggest using `/opsx:propose` instead
