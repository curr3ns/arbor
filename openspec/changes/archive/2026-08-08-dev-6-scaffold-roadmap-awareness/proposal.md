# Give arbor-project-scaffold roadmap awareness

## Why

A fresh project should land with the directory layout the rest of the arbor loop
expects, so the first `arbor-auto-roadmap` run has somewhere to write. Today a
scaffolded repo has no `docs/roadmaps/`, so the first planning run must create it
as a side effect, and nothing in the scaffold tells the user that planning is the
next move.

## What changes

- Scaffolding creates `docs/roadmaps/` and `docs/roadmaps/archive/`, each with a
  `.gitkeep` so both survive the initial commit while empty.
- The skill names `arbor-auto-roadmap` as the natural next step after scaffolding.
- No new interrogation questions are added to the existing question set.
