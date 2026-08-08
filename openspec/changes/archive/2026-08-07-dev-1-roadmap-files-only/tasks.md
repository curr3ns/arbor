## 1. Removals — strip the GitHub format

- [x] 1.1 Delete the `## Setup (GitHub format only, once per repo)` section in full, including the `gh auth status` / `gh repo view` step and the `roadmap` label step, from `.claude/skills/arbor-auto-roadmap/SKILL.md`. Verify: no `gh ` invocation and no `Setup` heading remain in the file.
- [x] 1.2 Delete interrogation step 1 (**Format**), the question offering `docs/roadmap/` vs GitHub, and the "check signal / user's call" guidance. Verify: the interrogation's first question is now name and vision.
- [x] 1.3 Delete generate step 8 (**GitHub format**) in full — tracking issue, per-phase Milestones, the `gh api .../milestones` command, and the per-milestone numbering note. Verify: `milestone`, `Milestone`, and `tracking issue` appear nowhere in the file.
- [x] 1.4 Remove "format" from the step 6 recap list so it restates name, vision, non-goals, and every phase with its items. Verify: the recap no longer asks the user to confirm a format that is no longer chosen.
- [x] 1.5 Renumber all remaining steps to run 1..N with no gaps, and keep the "create a todo per step and complete them in order" instruction consistent with the new numbering. Verify: step numbers are contiguous and every cross-reference in the body (e.g. "the step N recap") points at the right step.

## 2. Path and template — plural `docs/roadmaps/`

- [x] 2.1 Replace every occurrence of the singular `docs/roadmap/` with plural `docs/roadmaps/` in the body, the generate step, the template, and the guardrails. Verify: `grep -n 'docs/roadmap/' SKILL.md` returns no match while `docs/roadmaps/` is present.
- [x] 2.2 Retitle the surviving generate step from "Code format — write `docs/roadmap/<slug>.md`" to an unconditional write of `docs/roadmaps/<slug>.md`, with no "format" qualifier. Verify: the step reads as the only output path, not as one of two branches.
- [x] 2.3 Keep the roadmap Markdown template (title, vision paragraph, `## Non-goals`, `## Phase N: <name>`, `- [ ] **R<n>** <item>`) intact under the new step. Verify: the fenced template block still shows all four structural parts and the `- [ ] **R<n>**` item shape.

## 3. Semantics — checkbox, IDs, item reference, archive

- [x] 3.1 Document a checked box as meaning "implemented, gated, and merged." Verify: the phrase appears, and no text anywhere in the file says a checked box means refined, filed, or queued.
- [x] 3.2 Rewrite any statement that assigns checkbox-flipping or roadmap close-out to `arbor-auto-refine` so it reflects the new model (the box is flipped after the work is gated and merged, never by this skill). Verify: no surviving sentence claims refine flips boxes at issue-filing time.
- [x] 3.3 Collapse the ID rules to the single file-scoped rule: `R<n>` sequential across the whole file, assigned once, permanent, never reused or renumbered; a dropped item's line is deleted and its number retired; the next new item takes max-used + 1. Verify: exactly one numbering scope is described and no rule restarts IDs within a subdivision.
- [x] 3.4 Replace the `## The "Roadmap:" reference line (shared contract)` section with an item-reference section defining `docs/roadmaps/<slug>.md#R<n>`, documented as an argument passed to `arbor-auto-work` to name the item a work cycle is building — not a line written into an issue body. Verify: neither `Roadmap: docs/roadmap/...` nor `Roadmap: milestone #` survives, and the new format appears with `arbor-auto-work` named as its consumer.
- [x] 3.5 Document that a roadmap whose every item is checked ends up at `docs/roadmaps/archive/`, and that this skill does not perform the move. Verify: the archive path appears and is not framed as an action this skill takes.

## 4. Preserve the interrogation and guardrails

- [x] 4.1 Confirm the interrogation still covers name and vision, non-goals, phases (names, themes, sequence), and items per phase — each item a "why" plus acceptance criteria, sized like a single OpenSpec change, split in two when too big. Verify by reading the renumbered interrogation against the pre-change step list.
- [x] 4.2 Confirm `AskUserQuestion`, the one-topic-per-question rule, and the todo-per-step rule are all still stated. Verify: each appears verbatim or with equivalent force.
- [x] 4.3 Confirm the "generate nothing until the recap is approved" rule survives both at the top of the file and as a guardrail, with no file written before approval. Verify: both statements are present and agree.
- [x] 4.4 Confirm the strictly-sequential-phases guardrail survives, restated so "unchecked" means not yet implemented and merged. Verify: the guardrail names the earliest phase with an unchecked item as the only eligible source of work.
- [x] 4.5 Confirm the multiple-concurrent-roadmaps allowance survives, phrased for files only (several `docs/roadmaps/*.md`), with the "several open tracking issues" clause dropped. Verify: the guardrail mentions files and no GitHub objects.
- [x] 4.6 Confirm the verify/read-back step survives as the last generate step. Verify: the final step reads the written roadmap back before the run ends.
- [x] 4.7 Confirm the guardrails still state that this skill never flips its own checkboxes and is only ever human-invoked, never auto-invoked by another skill or run on a timer. Verify: both claims are present in the guardrails.

## 5. Frontmatter

- [x] 5.1 Rewrite the frontmatter `description` to describe the files-only roadmap under `docs/roadmaps/`, the item-reference format consumed by `arbor-auto-work`, and the human-invoked-only nature — dropping the Milestones option, the pinned tracking issue, and the refine checkbox-flip hand-off. Verify: the description mentions no removed behavior and matches what the body now does.
- [x] 5.2 Bump `metadata.version` from `1.2` to `1.3`. Verify: the frontmatter parses and the value is greater than the previous one.

## 6. Scope check and final verification

- [x] 6.1 Confirm the working tree changes nothing outside `.claude/skills/arbor-auto-roadmap/SKILL.md` and `openspec/`. Verify: `git status --porcelain` lists no other path, and specifically no change under `.claude/skills/arbor-auto-refine/`, `arbor-auto-work/`, `arbor-auto-developer/`, `arbor-opsx-auto/`, or `arbor-project-scaffold/`.
- [x] 6.2 Confirm `docs/roadmaps/roadmap-native-workcycles.md` is untouched — its bookkeeping is handled outside this change. Verify: it does not appear in `git status`.
- [x] 6.3 Confirm surviving `arbor-auto-refine` references in retained sections were left in place rather than scrubbed (scrubbing is a later roadmap item). Verify: references that neither live in removed sections nor assert the old checkbox semantics are still present.
- [x] 6.4 Read the rewritten `SKILL.md` end to end against every requirement in `specs/roadmap-planning/spec.md`, and diff it against the pre-change version to confirm nothing on the preserve list was lost during renumbering. Verify: every requirement's scenarios hold, and the diff shows only intended removals.
