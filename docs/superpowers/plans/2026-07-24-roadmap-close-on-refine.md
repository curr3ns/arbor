# Roadmap Closes at Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move roadmap-item closing from `arbor-auto-developer` (at merge time) to `arbor-auto-refine` (at issue-filing time), and stop `arbor-auto-refine` from ever invoking `arbor-auto-roadmap`'s interrogation or gating its whole cycle on a roadmap existing.

**Architecture:** Three `SKILL.md` prose specs get edited in place — no application code, no automated test suite. "Testing" here means: after each file's edits, grep for the specific old phrases that must be gone and the specific new phrases that must be present, then do one full read-through per file for internal consistency. A final task greps across all three files together for cross-references that got missed.

**Tech Stack:** Markdown skill specs (YAML frontmatter + prose), read/edited directly. `grep`/`rg` for verification.

## Global Constraints

- Every wording change is copied verbatim from the approved design doc at `docs/superpowers/specs/2026-07-24-roadmap-close-on-refine-design.md` — do not paraphrase differently than what's specified in this plan's steps.
- Bump each file's `metadata.version` frontmatter field by one minor version: `arbor-auto-roadmap` 1.1 → 1.2, `arbor-auto-refine` 1.2 → 1.3, `arbor-auto-developer` 1.3 → 1.4.
- Never touch any file outside `.claude/skills/arbor-auto-roadmap/SKILL.md`, `.claude/skills/arbor-auto-refine/SKILL.md`, `.claude/skills/arbor-auto-developer/SKILL.md`.
- Use the `Edit` tool with exact `old_string`/`new_string` blocks as given in each step — every block below is copy-paste-ready, not a paraphrase to improvise from.

---

### Task 1: `arbor-auto-roadmap/SKILL.md` — hand off ownership of closing

**Files:**
- Modify: `.claude/skills/arbor-auto-roadmap/SKILL.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the new contract text ("checkbox means refined into backlog, `arbor-auto-refine` flips it at filing time") that Tasks 2 and 3 both reference when describing who owns what.

- [ ] **Step 1: Bump the version and rewrite the description line**

```yaml
---
name: arbor-auto-roadmap
description: Interrogates the user to build a multi-phase product roadmap, then writes it either as versioned files under docs/roadmap/ or as GitHub Milestones (one per phase, plus a pinned tracking issue) — the user's choice. Use when planning or re-planning product direction beyond a single slice of work: phases, themes, sequencing, non-goals. Defines the "Roadmap:" reference-line format that arbor-auto-refine reads to turn the earliest incomplete phase's items into backlog issues — and, in that same run, flips each item's checkbox and closes the phase/roadmap out (archiving the file, or closing the Milestone and, if it was the last one, the pinned tracking issue) as soon as the item is filed. Purely user-invoked when there's planning to do, not on a timer — neither arbor-auto-refine nor arbor-auto-developer ever invoke it automatically.
license: MIT
metadata:
  author: arbor
  version: "1.2"
---
```

Use the `Edit` tool with:
- `old_string`: the current frontmatter block (lines 1-8, from `---` through the closing `---`, exactly as it reads today).
- `new_string`: the block above.

- [ ] **Step 2: Rewrite the intro paragraph**

- `old_string`:
```
Companion to `arbor-auto-refine` (agent 1) and `arbor-auto-developer` (agent 2)
in the continuous dev loop, but not itself part of that loop's cadence — this
skill runs either because a human invoked it directly when there's planning to
do, or because `arbor-auto-refine` invoked it mid-cycle as a precondition
fix-up (its own cycle requires a roadmap to exist and finds none). Either way
it interrogates whoever is present via `AskUserQuestion`, produces one
roadmap, and stops. The other two skills poll what it produces; it never
polls anything itself.
```
- `new_string`:
```
Companion to `arbor-auto-refine` (agent 1) and `arbor-auto-developer` (agent 2)
in the continuous dev loop, but not itself part of that loop's cadence or
invoked by either of them — this skill only ever runs because a human invoked
it directly when there's planning to do. It interrogates whoever is present
via `AskUserQuestion`, produces one roadmap, and stops. The other two skills
poll what it produces (`arbor-auto-refine` reads and closes it out;
`arbor-auto-developer` never touches it); it never polls anything itself.
```

- [ ] **Step 3: Rewrite the "Roadmap:" reference-line contract section**

- `old_string`:
```
## The "Roadmap:" reference line (shared contract)

Every backlog issue `arbor-auto-refine` files from a roadmap item carries,
verbatim, one line in its body:

- Code format: `Roadmap: docs/roadmap/<file>.md#R<n>`
- GitHub format: `Roadmap: milestone #<milestone-number> item R<n>`

`arbor-auto-developer` greps the body of the issue whose work just merged to
the integration branch (`gh issue view <n> --json body`) for this line to
decide whether — and where — to mark an item off, doing so right away rather
than waiting for the eventual default-branch close. No line means an ordinary
issue; skip the mark-off step.
```
- `new_string`:
```
## The "Roadmap:" reference line (shared contract)

Every backlog issue `arbor-auto-refine` files from a roadmap item carries,
verbatim, one line in its body:

- Code format: `Roadmap: docs/roadmap/<file>.md#R<n>`
- GitHub format: `Roadmap: milestone #<milestone-number> item R<n>`

This checkbox means "refined into the backlog," not "shipped."
`arbor-auto-refine` flips it itself, in the same run it files the issue (its
step 8/9) — it never waits for that issue to merge. `arbor-auto-developer`
never reads this line and never touches roadmap content; once an issue is
filed, that item's roadmap bookkeeping is already done, and
`arbor-auto-developer`'s only remaining job on it is closing the GitHub issue
itself via `Closes #N` at merge time.
```

- [ ] **Step 4: Rewrite the Guardrails section**

- `old_string`:
```
## Guardrails

- No files or GitHub objects created before the step 6 recap is approved.
- Phases are strictly sequential: `arbor-auto-refine` only ever proposes items
  from the earliest phase that still has an unchecked item — never a later
  phase while an earlier one is incomplete.
- Item IDs are permanent once written — never renumbered, never reused after
  an item is dropped.
- Multiple concurrent roadmaps (several `docs/roadmap/*.md` files, or several
  open tracking issues) are fine; each is tracked and archived independently.
- This skill only ever writes a *new* roadmap or extends one it's re-invoked
  on — marking items off and archiving completed roadmaps belongs to
  `arbor-auto-developer`, never to this skill.
```
- `new_string`:
```
## Guardrails

- No files or GitHub objects created before the step 6 recap is approved.
- Phases are strictly sequential: `arbor-auto-refine` only ever proposes items
  from the earliest phase that still has an unchecked item (unchecked means
  "not yet filed as a backlog issue") — never a later phase while an earlier
  one is incomplete.
- Item IDs are permanent once written — never renumbered, never reused after
  an item is dropped.
- Multiple concurrent roadmaps (several `docs/roadmap/*.md` files, or several
  open tracking issues) are fine; each is tracked and closed out
  independently.
- This skill only ever writes a *new* roadmap or extends one it's re-invoked
  on — flipping checkboxes and closing out completed roadmaps belongs to
  `arbor-auto-refine`, never to this skill. Neither `arbor-auto-refine` nor
  `arbor-auto-developer` ever invoke this skill automatically; it is only
  ever run by a human.
```

- [ ] **Step 5: Verify the old phrases are gone and new ones landed**

Run:
```bash
grep -n "precondition fix-up\|requires a roadmap to exist\|marking items off and archiving completed roadmaps belongs to\|arbor-auto-developer.*mark.*off\|greps the body of the issue whose work just merged" .claude/skills/arbor-auto-roadmap/SKILL.md
```
Expected: no output (empty match).

Run:
```bash
grep -n "version: \"1.2\"\|only ever run by a human\|refined into the backlog" .claude/skills/arbor-auto-roadmap/SKILL.md
```
Expected: three matching lines (one per phrase).

- [ ] **Step 6: Read the whole file back and check it reads coherently**

Read `.claude/skills/arbor-auto-roadmap/SKILL.md` in full; confirm no leftover reference to `arbor-auto-refine` invoking this skill, and that the "Setup" section (GitHub format only) still makes sense unchanged.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/arbor-auto-roadmap/SKILL.md
git commit -m "Hand roadmap close-out ownership from developer to refine (roadmap side)"
```

---

### Task 2: `arbor-auto-refine/SKILL.md` — own the close-out, drop the interrogation gate

**Files:**
- Modify: `.claude/skills/arbor-auto-refine/SKILL.md`

**Interfaces:**
- Consumes: the contract text from Task 1 ("checkbox means refined, flipped at filing time").
- Produces: the new step 9 ("Close out refined roadmap items") that Task 3 references when explaining why `arbor-auto-developer` no longer does mark-off.

- [ ] **Step 1: Bump the version and rewrite the description line**

- `old_string`:
```
---
name: arbor-auto-refine
description: Audit this repo's state and the running app to keep the issue backlog topped up with well-scoped, deduped work items — static doc/vision review, roadmap audit (docs/roadmap/ or GitHub Milestones written by arbor-auto-roadmap), dynamic app exploration for bugs, and triage of issues arbor-auto-developer left blocked. Requires an existing roadmap as a precondition for the whole cycle — invokes arbor-auto-roadmap first if none exists. Run on a schedule (~every 8h); each run is a single pass, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.2"
---
```
- `new_string`:
```
---
name: arbor-auto-refine
description: Audit this repo's state and the running app to keep the issue backlog topped up with well-scoped, deduped work items — static doc/vision review, roadmap audit (docs/roadmap/ or GitHub Milestones written by arbor-auto-roadmap), dynamic app exploration for bugs, and triage of issues arbor-auto-developer left blocked. When the roadmap audit files an item's backlog issue, immediately flips that item's checkbox and closes the phase/roadmap out (archiving the file, or closing the Milestone and pinned tracking issue) — never waits for the issue to merge, and never invokes arbor-auto-roadmap itself; a roadmap is optional input, not a precondition. Run on a schedule (~every 8h); each run is a single pass, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.3"
---
```

- [ ] **Step 2: Rewrite the Setup section**

- `old_string`:
```
## Setup (once, before the first scheduled run)

1. Confirm `gh auth status` works and note the repo
   (`gh repo view --json nameWithOwner`).
2. Confirm the labels `agent:backlog`, `type:dev`, `type:infra` (or the
   repo's own established types), `priority:1`, `priority:2`, `priority:3`
   exist (`gh label list`); if any are missing, that's a setup problem to fix
   before relying on the loop, not something to paper over per-run.
3. A roadmap (`docs/roadmap/*.md` or an open Milestone) is a precondition for
   this skill's cycle — see step 2. Roadmap content itself is always authored
   by `arbor-auto-roadmap`, whether a human ran it ahead of time or this skill
   invokes it mid-run; this skill never authors roadmap content itself.
```
- `new_string`:
```
## Setup (once, before the first scheduled run)

1. Confirm `gh auth status` works and note the repo
   (`gh repo view --json nameWithOwner`).
2. Confirm the labels `agent:backlog`, `type:dev`, `type:infra` (or the
   repo's own established types), `priority:1`, `priority:2`, `priority:3`
   exist (`gh label list`); if any are missing, that's a setup problem to fix
   before relying on the loop, not something to paper over per-run.
3. A roadmap (`docs/roadmap/*.md` or an open Milestone) is optional input, not
   a precondition — when none exists, the roadmap audit source (step 4)
   simply has nothing to contribute; every other source still runs. Roadmap
   content itself is always authored by `arbor-auto-roadmap`, and this skill
   never invokes it — planning the next roadmap is a human's call, made on
   their own schedule.
4. Confirm the integration branch `arbor-auto-developer`'s Setup already
   picked (`gh api repos/{owner}/{repo}/branches/<branch>`) — needed to commit
   docs-format roadmap bookkeeping (checkbox flips, archiving) directly to it
   in step 9. GitHub-format bookkeeping needs no branch at all.
```

- [ ] **Step 3: Rewrite step 2 ("Roadmap precondition" → "Roadmap check")**

- `old_string`:
```
2. **Roadmap precondition.** Check whether a roadmap exists: any non-archived
   `docs/roadmap/*.md` file, or any open Milestone. If none exists, invoke the
   `arbor-auto-roadmap` skill now — it interrogates whoever is present via
   `AskUserQuestion` and, once its recap is approved, writes the roadmap. If
   that interrogation doesn't end in an approved roadmap (abandoned,
   declined, or otherwise left incomplete), stop the run here: send the
   no-roadmap notification (see Notifications) and exit — every step below
   requires a roadmap and has nothing to do without one. Once a roadmap
   exists (already there, or just created), continue to step 3 with it.
```
- `new_string`:
```
2. **Roadmap check.** Check whether a roadmap exists: any non-archived
   `docs/roadmap/*.md` file, or any open Milestone. This is informational
   only — it decides whether step 4 has any candidates to contribute this
   run, not whether the run continues. If none exists, skip step 4 entirely
   and continue to step 3; never invoke `arbor-auto-roadmap` — planning the
   next roadmap is a human's call, on their own schedule.
```

- [ ] **Step 4: Rewrite step 4 ("Roadmap audit")**

- `old_string`:
```
4. **Roadmap audit.** Read the roadmap(s) confirmed or created in step 2 per
   the format `arbor-auto-roadmap` defines. For each roadmap found, find the
   earliest phase that still has any unchecked item — later phases in that
   same roadmap are not eligible this run, even if the queue has headroom.
   Unchecked items in that phase are candidates; when filed (step 8), each
   carries the `Roadmap:` reference line `arbor-auto-roadmap` defines, and
   (GitHub-format roadmaps only) gets assigned to that phase's Milestone.
```
- `new_string`:
```
4. **Roadmap audit.** Skip this source entirely if step 2 found no roadmap.
   Otherwise, read the roadmap(s) found, per the format `arbor-auto-roadmap`
   defines. For each roadmap, find the earliest phase that still has any
   unchecked item — later phases in that same roadmap are not eligible this
   run, even if the queue has headroom. Unchecked items in that phase are
   candidates; when filed (step 8), each carries the `Roadmap:` reference line
   `arbor-auto-roadmap` defines, and (GitHub-format roadmaps only) gets
   assigned to that phase's Milestone. Filing is also where the item's
   checkbox gets flipped and, if warranted, the phase/roadmap closed out —
   see step 9.
```

- [ ] **Step 5: Insert new step 9 after step 8 ("File issues, respecting the cap")**

- `old_string`:
```
   - If it came from the roadmap audit (step 4), also carries the `Roadmap:`
     reference line `arbor-auto-roadmap` defines, and, for a GitHub-format
     roadmap, is assigned to that phase's Milestone.

## Notifications
```
- `new_string`:
```
   - If it came from the roadmap audit (step 4), also carries the `Roadmap:`
     reference line `arbor-auto-roadmap` defines, and, for a GitHub-format
     roadmap, is assigned to that phase's Milestone.

9. **Close out refined roadmap items.** For every issue just filed in step 8
   that carries a `Roadmap:` reference line, flip that item's checkbox right
   away — don't wait for the issue to merge:
   - **Docs format:** edit the referenced `docs/roadmap/<file>.md`, checking
     `- [x] R<n>` for each newly-filed item. If every item in the file is now
     checked, `git mv` it to `docs/roadmap/archive/` in the same commit.
     Commit and push this directly to the integration branch confirmed in
     Setup — bookkeeping, not a new `arbor-auto-work` cycle. Batch every
     newly-filed item from this run into one commit.
   - **GitHub format:** PATCH the referenced Milestone's description (`gh api
     repos/{owner}/{repo}/milestones/<n>`) to check each newly-filed item's
     box. If every item in that Milestone is now checked, close it
     (`-f state=closed`). If that was the last open Milestone linked from the
     roadmap's pinned tracking issue, close the tracking issue too
     (`gh issue close`), leaving a closing comment that summarizes the
     phases.
   - If this closes out a whole roadmap (file archived, or tracking issue
     closed), send the roadmap-complete notification (see Notifications).

## Notifications
```

- [ ] **Step 6: Rewrite the Notifications section**

- `old_string`:
```
Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- The `agent:backlog` cap (5) is hit and no new issues were filed.
- The e2e stack has now failed to come up on two consecutive runs.
- No roadmap existed and the `arbor-auto-roadmap` interrogation (step 2)
  didn't end in one being written, so this run filed nothing.

Do **not** notify on a routine run that completes normally — that's noise,
not signal. If `PushNotification` isn't available in this run's environment,
leave a comment on the relevant issue instead and continue; don't fail the
run over a missing notification.
```
- `new_string`:
```
Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- The `agent:backlog` cap (5) is hit and no new issues were filed.
- The e2e stack has now failed to come up on two consecutive runs.
- Step 9 closes out a whole roadmap (file archived, or Milestone + tracking
  issue closed) — this is the signal that it's time for a human to plan the
  next one; there is no separate "no roadmap" notification since this skill
  never nags about a roadmap's absence.

Do **not** notify on a routine run that completes normally — that's noise,
not signal. If `PushNotification` isn't available in this run's environment,
leave a comment on the relevant issue instead and continue; don't fail the
run over a missing notification.
```

- [ ] **Step 7: Rewrite the Guardrails section**

- `old_string`:
```
## Guardrails

- Never run the static audit, roadmap audit, dynamic exploration, or
  blocked-issue triage sources without a roadmap in place first — a roadmap
  is a precondition for the whole cycle (step 2), not just for the roadmap
  audit specifically.
- Only ever touch the project's e2e/agent profile — never the default
  profile.
- Never file more than the queue allows; the cap is a hard stop, not a
  suggestion.
- Never re-open or edit an issue you didn't file, except to add a triage
  follow-up reference or a stack-failure tracking marker.
- Never propose an item from a later roadmap phase while an earlier phase in
  that same roadmap still has an unchecked item. Never author or edit a
  roadmap file or Milestone yourself — that's `arbor-auto-roadmap`'s job;
  this skill only ever invokes that skill (step 2) or reads what it already
  wrote.
- One run = one pass. Do not loop internally; exit when done and let the
  scheduler bring you back.
```
- `new_string`:
```
## Guardrails

- The roadmap audit source (step 4) only runs when a roadmap exists; its
  absence never blocks the static audit, dynamic exploration, or
  blocked-issue triage sources — those always run regardless.
- Only ever touch the project's e2e/agent profile — never the default
  profile.
- Never file more than the queue allows; the cap is a hard stop, not a
  suggestion.
- Never re-open or edit an issue you didn't file, except to add a triage
  follow-up reference or a stack-failure tracking marker.
- Never propose an item from a later roadmap phase while an earlier phase in
  that same roadmap still has an unchecked item.
- Never author new roadmap content — new phases, new items, or a new roadmap
  from scratch — that's `arbor-auto-roadmap`'s job, and this skill never
  invokes it. This skill only ever flips an existing item's checkbox and
  closes out a fully-refined file/Milestone/tracking issue that
  `arbor-auto-roadmap` already created.
- One run = one pass. Do not loop internally; exit when done and let the
  scheduler bring you back.
```

- [ ] **Step 8: Verify the old phrases are gone and new ones landed**

Run:
```bash
grep -n "Roadmap precondition\|invoke the \`arbor-auto-roadmap\` skill now\|no-roadmap notification\|precondition for the whole cycle" .claude/skills/arbor-auto-refine/SKILL.md
```
Expected: no output (empty match).

Run:
```bash
grep -n "version: \"1.3\"\|Close out refined roadmap items\|Roadmap check\." .claude/skills/arbor-auto-refine/SKILL.md
```
Expected: three matching lines.

- [ ] **Step 9: Read the whole file back and check step numbering**

Read `.claude/skills/arbor-auto-refine/SKILL.md` in full. Confirm "The cycle" section now runs 1 through 9 with no gap or duplicate number, and step 9 physically sits before the `## Notifications` heading.

- [ ] **Step 10: Commit**

```bash
git add .claude/skills/arbor-auto-refine/SKILL.md
git commit -m "Move roadmap close-out into refine, drop the interrogation gate"
```

---

### Task 3: `arbor-auto-developer/SKILL.md` — drop roadmap mark-off entirely

**Files:**
- Modify: `.claude/skills/arbor-auto-developer/SKILL.md`

**Interfaces:**
- Consumes: Task 2's new step 9 (referenced in prose as "where the checkbox already got flipped").
- Produces: nothing further downstream — this is the last file in the chain.

- [ ] **Step 1: Bump the version and rewrite the description line**

- `old_string`:
```
---
name: arbor-auto-developer
description: Poll for feedback on the integration branch's pull request (unresolved review comments, failing CI) first, then the issue backlog, implementing the highest-priority item one at a time via arbor-auto-work --autonomous overridden to integrate against a dedicated integration branch instead of the default branch. Keeps a single running PR from the integration branch to the default branch up to date for human review. When a merged issue carries arbor-auto-roadmap's "Roadmap:" reference line, marks that roadmap item off (archiving the file or closing the Milestone if it was the last one). Self-seeds the backlog with one arbor-auto-refine pass when the queue is empty and there's no PR feedback to address — that pass may itself invoke arbor-auto-roadmap if no roadmap exists yet, since arbor-auto-refine now requires one. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.3"
---
```
- `new_string`:
```
---
name: arbor-auto-developer
description: Poll for feedback on the integration branch's pull request (unresolved review comments, failing CI) first, then the issue backlog, implementing the highest-priority item one at a time via arbor-auto-work --autonomous overridden to integrate against a dedicated integration branch instead of the default branch. Keeps a single running PR from the integration branch to the default branch up to date for human review. Never touches roadmap content — arbor-auto-refine flips a roadmap item's checkbox and closes it out at filing time, not this skill at merge time. Self-seeds the backlog with one arbor-auto-refine pass when the queue is empty and there's no PR feedback to address. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.4"
---
```

- [ ] **Step 2: Simplify the self-seed step (3.2)**

- `old_string`:
```
   2. **Self-seed if empty.** If the queue is empty, run the `arbor-auto-refine`
      skill for exactly one pass (in-process — no subagent dispatch needed),
      then re-list open issues. That one pass may itself invoke
      `arbor-auto-roadmap` if no roadmap exists yet — `arbor-auto-refine`
      now requires one as a precondition for its own cycle — which can mean
      interrogating whoever is present before any issues get filed; this is
      still part of the same single pass, not a second invocation this skill
      needs to manage. Never invoke `arbor-auto-refine` a second time in
      the same run, regardless of what the one pass finds. If the queue is
      *still* empty after that one pass, **end the run now** — no dispatch,
      no notification, nothing else to do until the next scheduled tick.
```
- `new_string`:
```
   2. **Self-seed if empty.** If the queue is empty, run the `arbor-auto-refine`
      skill for exactly one pass (in-process — no subagent dispatch needed),
      then re-list open issues. Never invoke `arbor-auto-refine` a second
      time in the same run, regardless of what the one pass finds. If the
      queue is *still* empty after that one pass, **end the run now** — no
      dispatch, no notification, nothing else to do until the next scheduled
      tick.
```

- [ ] **Step 3: Remove the "Roadmap mark-off" paragraph from step 6 ("On success")**

- `old_string`:
```
   6. **On success:** the subagent's merge closes the issue via its
      `Closes #N` commit trailer once the integration branch itself reaches
      the default branch — verify the merge landed on the integration branch
      (`git log <integration-branch> --oneline -1` or equivalent). Then
      **ensure the running PR exists**: if no open PR from the integration
      branch to the default branch exists yet, open one now (title
      summarizing the batch, body listing accumulated work); if one already
      exists, its diff updates automatically from the push — nothing further
      to do.

      **Roadmap mark-off.** Check the issue's body
      (`gh issue view <n> --json body`) for the `Roadmap:` reference line
      `arbor-auto-roadmap` defines — don't wait for the eventual
      default-branch close to do this. If present: flip that item's checkbox
      in the referenced `docs/roadmap/*.md` file, `git mv`-ing it to
      `docs/roadmap/archive/` in the same commit if every item in the file is
      now checked; or, for a Milestone reference, PATCH the Milestone's
      description to flip the checkbox (`gh api
      repos/{owner}/{repo}/milestones/<n>`), closing the Milestone
      (`-f state=closed`) if every item in it is now checked. Commit and push
      this mark-off directly to the integration branch — it's bookkeeping,
      not a new `arbor-auto-work` cycle. No `Roadmap:` line means an ordinary
      issue; skip this step. Send the merge-landed notification.
```
- `new_string`:
```
   6. **On success:** the subagent's merge closes the issue via its
      `Closes #N` commit trailer once the integration branch itself reaches
      the default branch — verify the merge landed on the integration branch
      (`git log <integration-branch> --oneline -1` or equivalent). Then
      **ensure the running PR exists**: if no open PR from the integration
      branch to the default branch exists yet, open one now (title
      summarizing the batch, body listing accumulated work); if one already
      exists, its diff updates automatically from the push — nothing further
      to do. Send the merge-landed notification. This skill never touches
      roadmap content — if the issue carried a `Roadmap:` reference line,
      `arbor-auto-refine` already flipped that checkbox (and closed out the
      phase/roadmap, if warranted) back when it filed the issue.
```

- [ ] **Step 4: Remove the roadmap bullet from Notifications**

- `old_string`:
```
Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- A dispatched subagent's merge lands on the integration branch.
- PR feedback (review comments or failing CI) was addressed and pushed.
- An issue is left blocked after a second failed attempt.
- A roadmap mark-off archives its file (all phases complete) or closes its
  Milestone (fold this into the merge-landed notification above rather than
  sending a second one for the same event).

Do **not** notify when dispatching (only on the outcome), and do not notify
```
- `new_string`:
```
Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- A dispatched subagent's merge lands on the integration branch.
- PR feedback (review comments or failing CI) was addressed and pushed.
- An issue is left blocked after a second failed attempt.

Do **not** notify when dispatching (only on the outcome), and do not notify
```

- [ ] **Step 5: Replace the roadmap guardrail**

- `old_string`:
```
- At most one open PR from the integration branch to the default branch at a
  time — reuse it, never open a second.
- Never author or restructure roadmap content — only flip an existing
  checkbox or close an existing Milestone that `arbor-auto-roadmap` already
  created; that skill owns creation, this one only owns mark-off.
- P0/P1 (PR feedback) always takes priority over the issue queue in a given
```
- `new_string`:
```
- At most one open PR from the integration branch to the default branch at a
  time — reuse it, never open a second.
- Never touch roadmap content in any form — no checkbox, file, Milestone, or
  tracking issue. That's entirely `arbor-auto-refine`'s job now, done at
  issue-filing time.
- P0/P1 (PR feedback) always takes priority over the issue queue in a given
```

- [ ] **Step 6: Verify the old phrases are gone and new ones landed**

Run:
```bash
grep -n "Roadmap mark-off\|roadmap mark-off archives\|only flip an existing.*checkbox or close an existing Milestone\|now requires one as a precondition" .claude/skills/arbor-auto-developer/SKILL.md
```
Expected: no output (empty match).

Run:
```bash
grep -n "version: \"1.4\"\|never touches roadmap content\|Never touch roadmap content" .claude/skills/arbor-auto-developer/SKILL.md
```
Expected: three matching lines.

- [ ] **Step 7: Read the whole file back and check it reads coherently**

Read `.claude/skills/arbor-auto-developer/SKILL.md` in full; confirm the Subagent dispatch section and every other section untouched by this task still reads consistently with the rest.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/arbor-auto-developer/SKILL.md
git commit -m "Drop roadmap mark-off from developer now that refine owns it"
```

---

### Task 4: Cross-file consistency sweep

**Files:**
- Read-only check across all three: `.claude/skills/arbor-auto-roadmap/SKILL.md`, `.claude/skills/arbor-auto-refine/SKILL.md`, `.claude/skills/arbor-auto-developer/SKILL.md`

**Interfaces:**
- Consumes: the final state of all three files from Tasks 1-3.
- Produces: nothing — this task only verifies; if it finds a gap, fix it in the relevant file and re-run the grep before considering the task done.

- [ ] **Step 1: Grep all three for any remaining stale cross-reference**

Run:
```bash
grep -rn "precondition\|mark-off\|mark off\|invoke.*arbor-auto-roadmap\|invokes arbor-auto-roadmap" .claude/skills/arbor-auto-roadmap/SKILL.md .claude/skills/arbor-auto-refine/SKILL.md .claude/skills/arbor-auto-developer/SKILL.md
```
Expected: no matches. If any line surfaces, open that file and fix the specific sentence to match the new ownership model (refine flips/closes at filing time; developer never touches roadmap content; roadmap is never auto-invoked) before proceeding.

- [ ] **Step 2: Confirm every file's version bumped**

Run:
```bash
grep -n "version:" .claude/skills/arbor-auto-roadmap/SKILL.md .claude/skills/arbor-auto-refine/SKILL.md .claude/skills/arbor-auto-developer/SKILL.md
```
Expected:
```
.claude/skills/arbor-auto-roadmap/SKILL.md:  version: "1.2"
.claude/skills/arbor-auto-refine/SKILL.md:  version: "1.3"
.claude/skills/arbor-auto-developer/SKILL.md:  version: "1.4"
```

- [ ] **Step 3: Confirm `git status` is clean (everything committed)**

Run: `git status`
Expected: `nothing to commit, working tree clean` (Tasks 1-3 each committed their own file already — this just confirms nothing was left staged/modified from the consistency-sweep fixes, or if Step 1 required a fix, that fix has its own commit here).

If Step 1 required any fix, commit it now:
```bash
git add .claude/skills/<file>/SKILL.md
git commit -m "Fix stale cross-reference found in roadmap close-out consistency sweep"
```
