## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Change scope is limited to the roadmap skill

**Reason**: This requirement was authored by the preceding change (roadmap item R1) to freeze `arbor-auto-refine` in place while the roadmap contract was redefined. It forbade creating, modifying, moving, or deleting `arbor-auto-refine`, and required that surviving refine references inside `arbor-auto-roadmap` be left in place. Both clauses exist solely to defer the present change and are now directly contradicted by it: R2 deletes the skill and scrubs the references together, exactly as R1's design document (decision D3) intended. It also asserted that the only changed file outside `openspec/` is `arbor-auto-roadmap/SKILL.md`, which no longer holds now that a directory is deleted and `install.sh` is conditionally in scope.

**Migration**: Replaced by `Requirement: Change scope is limited to refine deletion and the roadmap scrub` in this capability, which keeps the protections that still apply (`arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` are untouched; the parent roadmap file is untouched) and inverts the two that no longer do. The deletion itself, and the requirement that nothing replaces refine, are specified by the new `skill-distribution` capability.
