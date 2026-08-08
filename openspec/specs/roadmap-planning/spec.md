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

The skill SHALL state that it only ever writes a new roadmap or extends one it is re-invoked on, and never flips a checkbox or archives a roadmap itself. The skill SHALL state that it is only ever run by a human and is never invoked automatically by another skill or on a timer. This auto-invocation guardrail SHALL be phrased so that it holds for every other skill rather than enumerating a roster, and SHALL NOT name any skill that the repo no longer ships.

#### Scenario: Non-mutation guardrail preserved

- **WHEN** the guardrails section is read
- **THEN** it states the skill never flips its own checkboxes and never closes out or archives a roadmap

#### Scenario: Human-invocation guardrail preserved

- **WHEN** the guardrails and the frontmatter description are read
- **THEN** both convey that the skill is human-invoked only and is not run on a schedule or triggered by another skill

#### Scenario: Guardrail names no deleted skill

- **WHEN** the auto-invocation guardrail is read
- **THEN** it asserts that no other skill invokes this one automatically
- **AND** it does not list `arbor-auto-refine` or any other skill absent from `.claude/skills/`

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

The skill's YAML frontmatter `description` SHALL describe the files-only roadmap under `docs/roadmaps/`, and SHALL NOT mention the GitHub Milestones option, the pinned tracking issue, or any hand-off in which another skill flips checkboxes and closes roadmaps out. The `description` SHALL NOT name `arbor-auto-refine` in any framing whatsoever, including as a skill that does *not* invoke this one. It SHALL still convey that the skill is human-invoked only and never runs on a timer or at another skill's initiative. The `metadata.version` value SHALL be increased above its previous value of `1.3`.

#### Scenario: Description matches the body

- **WHEN** the frontmatter `description` is read
- **THEN** it describes only behavior the body still implements
- **AND** it mentions neither GitHub Milestones nor a pinned tracking issue nor a checkbox flip performed by another skill

#### Scenario: Description names no deleted skill

- **WHEN** the frontmatter `description` is searched for `arbor-auto-refine`
- **THEN** there is no match, in any grammatical role

#### Scenario: Human-invoked-only claim survives the roster removal

- **WHEN** the frontmatter `description` is read
- **THEN** it still states that the skill is invoked by a user when there is planning to do, not on a timer and not automatically by another skill

#### Scenario: Version bumped

- **WHEN** `metadata.version` is compared against the previous value `1.3`
- **THEN** the new value is greater

### Requirement: No reference to arbor-auto-refine survives in the skill

`.claude/skills/arbor-auto-roadmap/SKILL.md` SHALL contain zero occurrences of the string `arbor-auto-refine`, in the YAML frontmatter and in the body alike. Every reference SHALL be replaced by a considered rewrite rather than deleted in place: the surrounding prose SHALL read naturally and completely, as though the skill had never existed, with no stub sentence, dangling conjunction, orphaned parenthetical, or claim left without its subject.

#### Scenario: The string does not appear anywhere in the file

- **WHEN** `grep -n 'arbor-auto-refine' .claude/skills/arbor-auto-roadmap/SKILL.md` is run
- **THEN** it produces no output and exits non-zero

#### Scenario: No rewrite leaves a scar

- **WHEN** each sentence that previously named `arbor-auto-refine` is read in its final form
- **THEN** it is a complete, grammatical statement that stands on its own
- **AND** it contains no empty slot, trailing "and", or dangling "(agent 2)"-style label where the removed name used to be

### Requirement: The skill's framing names only surviving consumers

The skill's opening framing SHALL describe its place in the system without reference to the retired two-agent loop. It SHALL name `arbor-auto-developer` reading `docs/roadmaps/*.md` directly as its work queue and `arbor-auto-work` building an item and marking it done, as the consumers of what this skill produces. It SHALL preserve, in substance, every claim the previous framing carried: this skill is not part of the loop's cadence, is never invoked by the loop, is only ever run directly by a human, polls nothing, produces one roadmap and stops, and never flips a box in a roadmap it wrote.

#### Scenario: Consumers are named accurately

- **WHEN** the opening framing is read
- **THEN** it identifies `arbor-auto-developer` as reading `docs/roadmaps/*.md` as its work queue and `arbor-auto-work` as the skill that builds an item and closes its box
- **AND** it contains no "agent 1"/"agent 2" numbering and no phrase such as "the other two skills"

#### Scenario: Every claim of the old framing survives

- **WHEN** the new framing is compared against the claims of the previous one
- **THEN** it still states that the skill is outside the loop's cadence, is not invoked by the loop, runs only when a human invokes it directly, polls nothing, produces one roadmap and stops, and never flips its own checkboxes

### Requirement: Interrogation rationales stand on their own

The rationale attached to the non-goals interrogation step and the rationale attached to the item-sizing instruction SHALL each be justified without appeal to any skill that no longer exists. The non-goals rationale SHALL explain why the user is asked for non-goals in terms of the roadmap itself — that it is the only place an exclusion is recorded, and that recording it is what stops scope from being quietly re-expanded later. The item-sizing rationale SHALL justify "sized like a single OpenSpec change" in terms of `arbor-auto-work` — one roadmap item becomes one work cycle: one branch, one gate, one merge — and SHALL retain the rule that an item too big to phrase that way becomes two items.

#### Scenario: Non-goals rationale is self-supporting

- **WHEN** the non-goals interrogation step is read
- **THEN** it gives a reason to capture non-goals that depends on no agent or skill existing
- **AND** it does not attribute future scope creep to a named skill

#### Scenario: Item-sizing rationale points at the real consumer

- **WHEN** the items-per-phase interrogation step is read
- **THEN** the "sized like a single OpenSpec change" instruction is justified by one item mapping to one `arbor-auto-work` cycle
- **AND** the "split an item too big to phrase that way into two" rule is still present

### Requirement: Change scope is limited to refine deletion and the roadmap scrub

Implementing this change SHALL modify only `.claude/skills/arbor-auto-refine/` (deleted in full), `.claude/skills/arbor-auto-roadmap/SKILL.md`, the OpenSpec artifacts for this change, and — if and only if the prune observation defined by the `skill-distribution` capability fails — `install.sh`. The skills `arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` SHALL NOT be created, modified, moved, or deleted. `docs/roadmaps/roadmap-native-workcycles.md` SHALL be read for context and SHALL NOT be modified.

#### Scenario: No other path is touched

- **WHEN** `git status --porcelain` is inspected after implementation
- **THEN** the only paths listed outside `openspec/` are the deletion under `.claude/skills/arbor-auto-refine/` and a modification to `.claude/skills/arbor-auto-roadmap/SKILL.md`
- **AND** `install.sh` appears only if the prune observation failed and required a fix
- **AND** no path under `.claude/skills/arbor-auto-work/`, `arbor-auto-developer/`, `arbor-opsx-auto/`, or `arbor-project-scaffold/` appears

#### Scenario: The parent roadmap file is left alone

- **WHEN** `git status --porcelain` is inspected
- **THEN** `docs/roadmaps/roadmap-native-workcycles.md` does not appear, because its checkbox bookkeeping is handled outside this change

#### Scenario: Refine references outside arbor-auto-roadmap are expected residue

- **WHEN** `arbor-auto-developer` is searched for `arbor-auto-refine` after this change
- **THEN** its references are still present and unmodified, which is the correct outcome — they are resolved by the parent roadmap's item R4, which rewrites that skill wholesale
- **AND** references surviving in other skills, in archived OpenSpec changes, and in git history are likewise out of scope
