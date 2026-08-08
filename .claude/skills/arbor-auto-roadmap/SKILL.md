---
name: arbor-auto-roadmap
description: Interrogates the user to build a multi-phase product roadmap, then writes it as versioned files under docs/roadmaps/ — one Markdown file per roadmap, one checkbox per item. Use when planning or re-planning product direction beyond a single slice of work: phases, themes, sequencing, non-goals. Defines the docs/roadmaps/<slug>.md#R<n> item-reference format, passed as an argument to arbor-auto-work to identify which item a work cycle is building — a box is checked only once that item has been implemented, gated, and merged. Purely user-invoked when there's planning to do, not on a timer — neither arbor-auto-refine nor arbor-auto-developer ever invoke it automatically.
license: MIT
metadata:
  author: arbor
  version: "1.3"
---

# Arbor auto-roadmap

Companion to `arbor-auto-refine` (agent 1) and `arbor-auto-developer` (agent 2)
in the continuous dev loop, but not itself part of that loop's cadence or
invoked by either of them — this skill only ever runs because a human invoked
it directly when there's planning to do. It interrogates whoever is present
via `AskUserQuestion`, produces one roadmap, and stops. The other two skills
poll what it produces; this skill polls nothing, and never flips a box in a
roadmap it wrote — a box is checked only once that item has been implemented,
gated, and merged.

**Generate nothing until the recap in step 5 is approved** — same rule as
`arbor-project-scaffold`.

## Phase 1 — Interrogate

You MUST create a todo per step and complete them in order. One topic per
question (`AskUserQuestion` where multiple-choice fits).

1. **Name and vision.** A short roadmap name (becomes the file slug) and a
   one-paragraph statement of the outcome and timeframe this roadmap covers.
2. **Non-goals.** What this roadmap explicitly does not cover — keeps
   `arbor-auto-refine` from later expanding scope back into something the user
   deliberately excluded.
3. **Phases.** Names and sequence — a roadmap is at least one phase, usually
   two to five. Phases are strictly ordered: later phases don't start until
   the earlier one's items are all checked off (see **Guardrails**).
4. **Items per phase.** For each phase, the shippable slices that make it up.
   Phrase each like a backlog issue: a "why" plus acceptance criteria, sized
   like a single OpenSpec change — the same sizing `arbor-auto-refine` already
   uses when it files issues. An item too big to phrase that way should become
   two items.
5. **Recap.** Restate name, vision, non-goals, and every phase with its
   items, and get an explicit go before writing anything.

## Phase 2 — Generate

6. **Write the roadmap** — create `docs/roadmaps/<slug>.md`:

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

7. **Verify.** Re-read what was written back to the user before ending the
   run — a roadmap only this skill produced and no one reviewed is not done.

## Item reference

A roadmap item is addressed as `docs/roadmaps/<slug>.md#R<n>` — the roadmap
file's slug plus the item's permanent ID. This is the string handed to
`arbor-auto-work` as an argument, to tell it which item the work cycle is
building; it is not a line written into a GitHub issue body.

A checked box (`- [x] **R<n>**`) means the item has been implemented, gated,
and merged — never "refined," "filed," or "queued." An unchecked box means
the work has not yet landed.

When every item in a roadmap is checked, the file moves to
`docs/roadmaps/archive/`. This skill does not perform that move; whoever
flips the roadmap's last box does.

## Guardrails

- No files created before the step 5 recap is approved.
- Phases are strictly sequential: only the earliest phase that still has an
  unchecked item is eligible for work — unchecked meaning not yet
  implemented and merged — never a later phase while an earlier one is
  incomplete.
- Item IDs are permanent once written — never renumbered, never reused after
  an item is dropped.
- Multiple concurrent roadmaps (several `docs/roadmaps/*.md` files) are
  fine; each is tracked and completed independently.
- This skill only ever writes a *new* roadmap or extends one it's re-invoked
  on — it never flips a checkbox and never archives or closes out a roadmap
  itself. Neither `arbor-auto-refine` nor `arbor-auto-developer` ever invoke
  this skill automatically; it is only ever run by a human.
