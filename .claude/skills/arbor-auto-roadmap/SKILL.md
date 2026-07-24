---
name: arbor-auto-roadmap
description: Interrogates the user to build a multi-phase product roadmap, then writes it either as versioned files under docs/roadmap/ or as GitHub Milestones (one per phase, plus a pinned tracking issue) — the user's choice. Use when planning or re-planning product direction beyond a single slice of work: phases, themes, sequencing, non-goals. Defines the "Roadmap:" reference-line format that arbor-auto-refine reads to turn the earliest incomplete phase's items into backlog issues — and, in that same run, flips each item's checkbox and closes the phase/roadmap out (archiving the file, or closing the Milestone and, if it was the last one, the pinned tracking issue) as soon as the item is filed. Purely user-invoked when there's planning to do, not on a timer — neither arbor-auto-refine nor arbor-auto-developer ever invoke it automatically.
license: MIT
metadata:
  author: arbor
  version: "1.2"
---

# Arbor auto-roadmap

Companion to `arbor-auto-refine` (agent 1) and `arbor-auto-developer` (agent 2)
in the continuous dev loop, but not itself part of that loop's cadence or
invoked by either of them — this skill only ever runs because a human invoked
it directly when there's planning to do. It interrogates whoever is present
via `AskUserQuestion`, produces one roadmap, and stops. The other two skills
poll what it produces (`arbor-auto-refine` reads and closes it out;
`arbor-auto-developer` never touches it); it never polls anything itself.

**Generate nothing until the recap in step 6 is approved** — same rule as
`arbor-project-scaffold`.

## Setup (GitHub format only, once per repo)

1. Confirm `gh auth status` works and note the repo
   (`gh repo view --json nameWithOwner`).
2. Confirm the `roadmap` label exists (`gh label list`); create it if missing
   (`gh label create roadmap --description "Roadmap tracking issue"`).

## Phase 1 — Interrogate

You MUST create a todo per step and complete them in order. One topic per
question (`AskUserQuestion` where multiple-choice fits).

1. **Format.** Ask code (`docs/roadmap/`) or GitHub (Milestones + a pinned
   tracking issue). If undecided, check signal: a repo with a GitHub remote
   and working `gh auth status` leans GitHub; otherwise lean code. Either way
   this is the user's call, not an inferred default — ask.
2. **Name and vision.** A short roadmap name (becomes the file slug or
   tracking-issue title) and a one-paragraph statement of the outcome and
   timeframe this roadmap covers.
3. **Non-goals.** What this roadmap explicitly does not cover — keeps
   `arbor-auto-refine` from later expanding scope back into something the user
   deliberately excluded.
4. **Phases.** Names and sequence — a roadmap is at least one phase, usually
   two to five. Phases are strictly ordered: later phases don't start until
   the earlier one's items are all checked off (see Phase 2).
5. **Items per phase.** For each phase, the shippable slices that make it up.
   Phrase each like a backlog issue: a "why" plus acceptance criteria, sized
   like a single OpenSpec change — the same sizing `arbor-auto-refine` already
   uses when it files issues. An item too big to phrase that way should become
   two items.
6. **Recap.** Restate format, name, vision, non-goals, and every phase with
   its items, and get an explicit go before writing anything.

## Phase 2 — Generate

7. **Code format** — write `docs/roadmap/<slug>.md`:

   ```markdown
   # <Roadmap name>

   <vision paragraph>

   ## Non-goals
   - <item>

   ## Phase 1: <phase name>
   - [ ] **R1** <item — why + acceptance criteria>
   - [ ] **R2** <item>

   ## Phase 2: <phase name>
   - [ ] **R3** <item>
   ```

   IDs (`R<n>`) are sequential across the whole file, assigned once, and never
   reused or renumbered — if an item is dropped later, delete its line and
   leave the number retired; the next new item still takes max-used + 1.

8. **GitHub format** — one Milestone per phase, plus a pinned tracking issue:
   - Tracking issue: title `Roadmap: <name>`, label `roadmap`, body holds the
     vision paragraph, the non-goals list, and a linked list of the phase
     Milestones (number + title) in order.
   - One Milestone per phase (`gh api repos/{owner}/{repo}/milestones -f
     title="<name> — Phase N: <phase name>" -f description="..."`). The
     description holds that phase's item checklist, same `- [ ] **R<n>**`
     scheme as the code format, IDs sequential *within that milestone's
     description* starting at `R1` (milestones are separate objects, so no
     global numbering across the roadmap — the reference line below always
     carries the milestone number alongside the item ID, which is enough to
     disambiguate).

9. **Verify.** Re-read what was written back to the user before ending the
   run — a roadmap only this skill produced and no one reviewed is not done.

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
