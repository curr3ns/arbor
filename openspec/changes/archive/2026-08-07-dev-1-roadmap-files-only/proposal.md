## Why

`arbor-auto-roadmap` currently writes a roadmap in one of two formats — files under `docs/roadmap/` or GitHub Milestones plus a pinned tracking issue — and the Milestones branch exists solely to feed `arbor-auto-refine`'s issue-filing path. As the roadmap becomes the work queue itself (see `docs/roadmaps/roadmap-native-workcycles.md`, item R1), there is exactly one consumer and one format, so the dual-format branch is dead weight and the checkbox semantics change: a checked box must mean "implemented, gated, and merged," not "refined into the backlog."

## What Changes

- **BREAKING** Remove the format interrogation (current step 1) — roadmaps are always files. There is no longer a user choice of output format.
- **BREAKING** Remove the entire GitHub Milestones + pinned-tracking-issue generation branch and the GitHub-only Setup section (`gh auth status`, `roadmap` label creation).
- **BREAKING** Rename the roadmap directory from singular `docs/roadmap/` to plural `docs/roadmaps/` everywhere in the skill.
- **BREAKING** Redefine checkbox semantics: a checked box means "implemented, gated, and merged," never "refined."
- **BREAKING** Replace the `Roadmap:` reference-line contract (a line in a GitHub issue body) with an item-reference format `docs/roadmaps/<slug>.md#R<n>`, documented as an argument passed to `arbor-auto-work`.
- Collapse the two ID-numbering rules (file-scoped and per-milestone) into the single file-scoped rule: `R<n>` is sequential across the file, permanent, never reused or renumbered.
- Document that a fully-checked roadmap ends up in `docs/roadmaps/archive/`.
- Update the YAML frontmatter `description` (it currently advertises the Milestones option and the refine hand-off, both removed) and bump `metadata.version`.
- Preserve unchanged: the product-direction interrogation (name/vision, non-goals, phases, themes, sequencing, items per phase), `AskUserQuestion` usage, one-topic-per-question, generate-nothing-until-recap-approved, strictly-sequential phases, multiple concurrent roadmaps, and the verify/read-back step.
- Preserve unchanged: the skill never flips its own checkboxes, and is only ever human-invoked.

## Capabilities

### New Capabilities
- `roadmap-planning`: The `arbor-auto-roadmap` skill's contract — how a human is interrogated for product direction, the files-only roadmap format written under `docs/roadmaps/`, the `R<n>` item-ID rules, the `docs/roadmaps/<slug>.md#R<n>` item-reference format consumed by `arbor-auto-work`, checkbox semantics, archival, and the skill's guardrails.

### Modified Capabilities
<!-- None. openspec/specs/ is empty; this is the first capability in the repo. -->

## Impact

- **Files changed**: `.claude/skills/arbor-auto-roadmap/SKILL.md` only (plus these OpenSpec artifacts). Nothing else in the repo is touched.
- **Explicitly out of scope**: `arbor-auto-refine`, `arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` are not modified or deleted. Removing `arbor-auto-refine` (and scrubbing its references out of `arbor-auto-roadmap`) is roadmap item R2, a separate later change; existing refine references inside `arbor-auto-roadmap` stay in place for now.
- **Downstream consumers**: `arbor-auto-refine` reads `docs/roadmap/` (singular) today and will not find roadmaps at the new plural path. This is expected and accepted — refine is deleted in R2. No migration tooling ships here (an explicit non-goal of the parent roadmap).
- **Verification**: this is a skills repo — the product is Markdown skill definitions under `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, and no gate command; verification is reading the rewritten Markdown against the acceptance criteria.
