# project-scaffolding Specification

## Purpose
TBD - created by archiving change dev-6-scaffold-roadmap-awareness. Update Purpose after archive.
## Requirements
### Requirement: Scaffolding creates the roadmap directory layout

`arbor-project-scaffold` SHALL create `docs/roadmaps/` and
`docs/roadmaps/archive/` during its generate phase, each containing a `.gitkeep`
file so both directories survive the initial commit while empty. The skill SHALL
NOT author any roadmap file, phase, or item.

#### Scenario: Both directories are created and tracked

- **WHEN** the scaffold's generate phase runs
- **THEN** `docs/roadmaps/.gitkeep` and `docs/roadmaps/archive/.gitkeep` both exist and are committed

#### Scenario: No roadmap content is invented

- **WHEN** the scaffold finishes
- **THEN** `docs/roadmaps/` contains no `.md` file, because what to build is the user's to plan

### Requirement: The skill names arbor-auto-roadmap as the next step

`arbor-project-scaffold` SHALL close by naming `arbor-auto-roadmap` as the
natural next step after scaffolding, and SHALL NOT invoke it or begin planning
itself.

#### Scenario: Hand-off is named, not performed

- **WHEN** the scaffold completes
- **THEN** it names `arbor-auto-roadmap` as the next step and stops without invoking it

### Requirement: No new interrogation questions are added

The change SHALL NOT add any question to the skill's existing Phase 1
interrogation set.

#### Scenario: Question set is unchanged

- **WHEN** Phase 1 is compared before and after the change
- **THEN** its questions are identical, and the roadmap layout is created in the generate phase without asking about it

