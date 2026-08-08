## ADDED Requirements

### Requirement: The repo no longer ships an arbor-auto-refine skill

The repository SHALL NOT contain a `.claude/skills/arbor-auto-refine/` directory. The removal SHALL be performed with `git rm -r` so that the deletion is staged in the git index, not merely absent from the working tree. No new or renamed skill SHALL be introduced to carry forward the behaviors refine provided — its static documentation audit, its dynamic exploration of the running app, its blocked-issue triage, and its backlog issue filing are dropped, not relocated.

#### Scenario: Skill directory is absent from the repo

- **WHEN** `.claude/skills/` is listed
- **THEN** no `arbor-auto-refine` entry appears
- **AND** no file under `.claude/skills/arbor-auto-refine/` exists on disk

#### Scenario: Deletion is staged in git, not only on the filesystem

- **WHEN** `git status --porcelain` is run after the removal
- **THEN** `.claude/skills/arbor-auto-refine/SKILL.md` appears with a staged deletion status (`D` in the index column), not as an unstaged working-tree deletion

#### Scenario: No replacement skill is created

- **WHEN** the set of directories under `.claude/skills/` is compared against the set before this change
- **THEN** the only difference is the removal of `arbor-auto-refine`
- **AND** no remaining skill has been given refine's doc-audit, app-exploration, triage, or issue-filing behavior

### Requirement: Installing prunes links for skills the repo no longer ships

`install.sh` SHALL remove any entry in `~/.claude/skills/` that is a symlink, points into this repo's `.claude/skills/` directory, and no longer resolves to an existing target. Entries that are not symlinks, and symlinks that point somewhere other than this repo's skills directory, SHALL be left untouched.

#### Scenario: Deleted skill's installed link is pruned by an actual run

- **WHEN** `~/.claude/skills/arbor-auto-refine` exists as a symlink into this repo's `.claude/skills/` directory, the `.claude/skills/arbor-auto-refine/` directory is then deleted, and `./install.sh` is run
- **THEN** `~/.claude/skills/arbor-auto-refine` no longer exists by any means — it is neither a live symlink, a dangling symlink, nor a regular file or directory

#### Scenario: Confirmation is an observation, not a code reading

- **WHEN** the prune behavior is claimed to hold
- **THEN** the evidence is the recorded before/after state of `~/.claude/skills/` around a real `./install.sh` invocation
- **AND** a reading of the prune loop's source is not accepted as sufficient evidence on its own

### Requirement: Installing preserves links for skills the repo still ships

`install.sh` SHALL leave every `~/.claude/skills/` symlink whose target still exists in this repo's `.claude/skills/` directory in place and pointing at that target. Creating links for shipped skills that were not previously installed is expected behavior and SHALL NOT be treated as damage.

#### Scenario: Every surviving arbor skill link is intact after the run

- **WHEN** `./install.sh` completes following the removal of `arbor-auto-refine`
- **THEN** each of `arbor-auto-developer`, `arbor-auto-roadmap`, `arbor-auto-work`, `arbor-code-commit`, `arbor-code-gencommit`, `arbor-opsx-auto`, `arbor-project-scaffold`, `arbor-workspace-add`, `arbor-workspace-create`, `arbor-workspace-import`, and `arbor-workspace-init` is still present in `~/.claude/skills/`
- **AND** each is still a symlink whose target resolves to the same-named directory inside this repo's `.claude/skills/`

#### Scenario: Newly linked shipped skills are not a regression

- **WHEN** `./install.sh` creates links for skills that ship in the repo but had no link before the run
- **THEN** those new links are expected output of the install step and do not constitute a failed verification

### Requirement: install.sh is modified only when the prune is observed to fail

`install.sh` SHALL be left byte-for-byte unchanged when the observed prune behavior satisfies the two requirements above. If and only if the observation fails SHALL `install.sh` be edited, and then only to make the prune remove links for skills the repo no longer ships while preserving the rest. No unrelated refactor, cleanup, or feature SHALL ride along with such a fix.

#### Scenario: Prune works, so the script is untouched

- **WHEN** the post-run observation shows refine's link removed and every surviving link intact
- **THEN** `install.sh` does not appear in `git status --porcelain`

#### Scenario: Prune fails, so the script is fixed narrowly

- **WHEN** the post-run observation shows refine's link still present, or a surviving link removed or repointed
- **THEN** `install.sh` is edited so that a subsequent run satisfies both prune and preservation requirements
- **AND** the diff to `install.sh` touches only the linking and pruning logic implicated by the failure
