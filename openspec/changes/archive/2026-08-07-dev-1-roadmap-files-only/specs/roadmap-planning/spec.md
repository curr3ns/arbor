## ADDED Requirements

### Requirement: Roadmaps are written as files only

The `arbor-auto-roadmap` skill SHALL write every roadmap as a Markdown file at `docs/roadmaps/<slug>.md`. The skill SHALL NOT offer, ask about, or support any alternative output format. The skill SHALL NOT create GitHub Milestones, tracking issues, or labels, and SHALL NOT require any GitHub setup step before running.

#### Scenario: Skill body contains no format choice

- **WHEN** `.claude/skills/arbor-auto-roadmap/SKILL.md` is read end to end
- **THEN** it contains no step asking the user to choose between a file format and a GitHub format
- **AND** it contains no GitHub Milestones generation instructions, no pinned-tracking-issue instructions, and no `Setup` section covering `gh auth status` or `roadmap` label creation
- **AND** the only documented output location is `docs/roadmaps/<slug>.md`

#### Scenario: Generation phase writes one file

- **WHEN** the skill reaches its generate phase after an approved recap
- **THEN** it writes exactly one Markdown file at `docs/roadmaps/<slug>.md` using the documented roadmap template

### Requirement: Roadmap directory is plural throughout

The skill SHALL refer to the roadmap directory as `docs/roadmaps/` (plural) in every occurrence, including the frontmatter `description`, the generation template, the item-reference format, the guardrails, and the archive path. The singular form `docs/roadmap/` SHALL NOT appear anywhere in the file.

#### Scenario: No singular path survives

- **WHEN** `.claude/skills/arbor-auto-roadmap/SKILL.md` is searched for `docs/roadmap/`
- **THEN** every match is part of the plural `docs/roadmaps/`, and no occurrence of the singular directory path remains

### Requirement: A checked box means implemented, gated, and merged

The skill SHALL document that a checked roadmap item (`- [x] **R<n>**`) means the item has been implemented, has passed the project's gate, and has been merged. The skill SHALL NOT describe a checked box as meaning "refined," "filed as a backlog issue," or any state short of merged. An unchecked item SHALL be documented as work that has not yet landed.

#### Scenario: Semantics stated once and unambiguously

- **WHEN** the skill's documentation of checkbox meaning is read
- **THEN** it states that a checked box means implemented, gated, and merged
- **AND** no statement anywhere in the file equates a checked box with an item having been refined into a backlog

#### Scenario: Sequential-phase rule uses the new meaning

- **WHEN** the guardrail on strictly sequential phases is read
- **THEN** "incomplete" and "unchecked" are defined in terms of work not yet implemented and merged, not in terms of work not yet filed as an issue

### Requirement: Item IDs follow one file-scoped rule

The skill SHALL define exactly one ID-numbering rule: `R<n>` identifiers are sequential across the whole roadmap file, assigned once, permanent, and never reused or renumbered. When an item is dropped, its line SHALL be deleted and its number retired, and the next new item SHALL take the highest-used number plus one. No per-milestone, per-phase, or otherwise scoped numbering rule SHALL appear.

#### Scenario: Only the file-scoped rule is documented

- **WHEN** the skill's ID rules are read
- **THEN** exactly one numbering scope is described — the whole file
- **AND** no rule describes IDs restarting at `R1` within a milestone, phase, or other subdivision

#### Scenario: Retired IDs are not reused

- **WHEN** an author drops an item from an existing roadmap and later adds a new one
- **THEN** the skill instructs that the dropped number stays retired and the new item takes max-used + 1

### Requirement: Item reference is an argument to arbor-auto-work

The skill SHALL define the item-reference format `docs/roadmaps/<slug>.md#R<n>` and SHALL document it as a value passed as an argument to `arbor-auto-work` to identify the roadmap item a work cycle is building. The skill SHALL NOT define, describe, or retain the `Roadmap:` reference line placed in a GitHub issue body, in either its file or milestone dialect.

#### Scenario: Reference format documented as an argument

- **WHEN** the item-reference section of the skill is read
- **THEN** the format is given as `docs/roadmaps/<slug>.md#R<n>`
- **AND** it is described as being handed to `arbor-auto-work`, not as a line written into an issue body

#### Scenario: Old reference-line contract is gone

- **WHEN** the skill is searched for the `Roadmap:` reference-line contract
- **THEN** neither `Roadmap: docs/roadmap/<file>.md#R<n>` nor `Roadmap: milestone #<n> item R<n>` appears

### Requirement: Completed roadmaps end up archived

The skill SHALL document that a roadmap whose every item is checked ends up at `docs/roadmaps/archive/`, so that authors understand the file's lifecycle and a re-invocation does not treat an archived roadmap as live.

#### Scenario: Archive destination is stated

- **WHEN** the skill's description of a completed roadmap is read
- **THEN** it names `docs/roadmaps/archive/` as where a fully-checked roadmap ends up

### Requirement: The skill never flips checkboxes and is only human-invoked

The skill SHALL state that it only ever writes a new roadmap or extends one it is re-invoked on, and never flips a checkbox or archives a roadmap itself. The skill SHALL state that it is only ever run by a human and is never invoked automatically by another skill or on a timer.

#### Scenario: Non-mutation guardrail preserved

- **WHEN** the guardrails section is read
- **THEN** it states the skill never flips its own checkboxes and never closes out or archives a roadmap

#### Scenario: Human-invocation guardrail preserved

- **WHEN** the guardrails and the frontmatter description are read
- **THEN** both convey that the skill is human-invoked only and is not run on a schedule or triggered by another skill

### Requirement: Product-direction interrogation is preserved

The skill SHALL retain its interrogation of the user covering: roadmap name and vision, non-goals, phases (names, themes, and sequence), and the shippable items making up each phase, each phrased with a "why" plus acceptance criteria and sized like a single OpenSpec change. The interrogation SHALL use `AskUserQuestion`, SHALL cover one topic per question, and SHALL create a todo per step completed in order.

#### Scenario: All interrogation topics survive

- **WHEN** the interrogation phase is read
- **THEN** it asks about name and vision, non-goals, phases and their sequence, and items per phase
- **AND** it directs the use of `AskUserQuestion` with one topic per question

#### Scenario: Item sizing guidance survives

- **WHEN** the items-per-phase step is read
- **THEN** it requires each item to carry a "why" plus acceptance criteria, sized like a single OpenSpec change, and to be split in two when too big to phrase that way

### Requirement: Nothing is generated before the recap is approved

The skill SHALL restate the roadmap name, vision, non-goals, and every phase with its items back to the user, and SHALL obtain an explicit go-ahead before writing any file. No file SHALL be created before that approval.

#### Scenario: Recap gate holds

- **WHEN** the user has answered every interrogation question but has not approved the recap
- **THEN** the skill has written no files

### Requirement: Phases are strictly sequential

The skill SHALL document that phases are strictly ordered: a later phase is not started while an earlier phase still has an unchecked item.

#### Scenario: Ordering rule documented

- **WHEN** the guardrails are read
- **THEN** they state that items are only worked from the earliest phase that still has an unchecked item, never from a later phase while an earlier one is incomplete

### Requirement: Multiple concurrent roadmaps are allowed

The skill SHALL document that several roadmap files may exist under `docs/roadmaps/` at once, each tracked and completed independently.

#### Scenario: Concurrency allowance preserved

- **WHEN** the guardrails are read
- **THEN** they permit multiple concurrent `docs/roadmaps/*.md` files, each closed out independently

### Requirement: The generated roadmap is read back for verification

The skill SHALL re-read what it wrote back to the user before ending the run, so that a roadmap no human reviewed is never considered done.

#### Scenario: Verify step preserved

- **WHEN** the generate phase completes
- **THEN** a final step reads the written roadmap back to the user before the run ends

### Requirement: Frontmatter describes the files-only behavior

The skill's YAML frontmatter `description` SHALL describe the files-only roadmap under `docs/roadmaps/`, and SHALL NOT mention the GitHub Milestones option, the pinned tracking issue, or a hand-off in which `arbor-auto-refine` flips checkboxes and closes roadmaps out. The `metadata.version` value SHALL be increased above its previous value.

#### Scenario: Description matches the body

- **WHEN** the frontmatter `description` is read
- **THEN** it describes only behavior the body still implements
- **AND** it mentions neither GitHub Milestones nor a pinned tracking issue nor a refine-driven checkbox flip

#### Scenario: Version bumped

- **WHEN** `metadata.version` is compared against the previous value `1.2`
- **THEN** the new value is greater

### Requirement: Change scope is limited to the roadmap skill

Implementing this change SHALL modify only `.claude/skills/arbor-auto-roadmap/SKILL.md` and the OpenSpec artifacts for this change. The skills `arbor-auto-refine`, `arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` SHALL NOT be created, modified, moved, or deleted. Pre-existing references to `arbor-auto-refine` that survive in retained sections of `arbor-auto-roadmap` SHALL be left in place, except where they assert checkbox semantics this change redefines.

#### Scenario: No other skill is touched

- **WHEN** the working tree is diffed after implementation
- **THEN** the only changed file outside `openspec/` is `.claude/skills/arbor-auto-roadmap/SKILL.md`
- **AND** `.claude/skills/arbor-auto-refine/`, `arbor-auto-work/`, `arbor-auto-developer/`, `arbor-opsx-auto/`, and `arbor-project-scaffold/` are unchanged

#### Scenario: Surviving refine references are not scrubbed

- **WHEN** a reference to `arbor-auto-refine` appears in a section this change retains and does not assert that refine flips checkboxes or closes roadmaps out
- **THEN** it is left as-is, because removing it belongs to a later roadmap item
