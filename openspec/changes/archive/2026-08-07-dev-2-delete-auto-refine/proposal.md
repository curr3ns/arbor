## Why

`arbor-auto-refine` flips a roadmap item's checkbox — and closes or archives the whole roadmap — at issue-*filing* time, before a line of the work exists. Roadmap item R1 (already shipped, see `docs/roadmaps/roadmap-native-workcycles.md`) redefined a checked box to mean "implemented, gated, and merged," so every refine pass now actively lies: it marks unbuilt work as done. Refine is the writer in that disagreement, so it has to be deleted in the same phase that redefined the checkbox, not a phase later. R1 also deliberately left refine's name scattered through `arbor-auto-roadmap` rather than have a live skill denied by the skill that feeds it; that deferral comes due here. This is roadmap item R2.

## What Changes

- **BREAKING** Delete the `arbor-auto-refine` skill: `.claude/skills/arbor-auto-refine/` is removed with `git rm -r`, so the deletion is staged in git rather than only present on the filesystem. Nothing replaces it — refine's static doc audit, dynamic app exploration, and blocked-issue triage are dropped, not relocated (an explicit non-goal of the parent roadmap).
- Confirm **empirically** that `install.sh` needs no change: its existing prune loop already removes dangling `~/.claude/skills/*` symlinks that point into this repo's skills directory. The confirmation is a real observation — run `./install.sh` after the deletion and check that `~/.claude/skills/arbor-auto-refine` is gone and every other arbor symlink survives intact. `install.sh` is modified **only if** that observation fails.
- **BREAKING** Scrub all five `arbor-auto-refine` references out of `.claude/skills/arbor-auto-roadmap/SKILL.md` (frontmatter `description` plus body lines ~12, ~32, ~39, ~100). Each is a considered rewrite, not a deletion: the surrounding prose must read as though refine never existed.
  - The opening "companion to refine (agent 1) and developer (agent 2)" framing becomes an accurate description of the post-refine world, in which `arbor-auto-developer` reads `docs/roadmaps/*.md` directly as its work queue and `arbor-auto-work` builds and closes items.
  - The non-goals rationale ("keeps refine from expanding scope") and the item-sizing note ("the same sizing refine uses when it files issues") get replacement rationales that stand on their own.
  - The guardrail asserting that neither refine nor developer auto-invokes this skill survives in spirit, naming only skills that still exist.
- Bump `metadata.version` in `.claude/skills/arbor-auto-roadmap/SKILL.md` above its current `1.3`.
- **BREAKING** (spec-level) Retire R1's scope requirement that froze `arbor-auto-refine` in place and mandated leaving its references in `arbor-auto-roadmap`. That rule existed to defer exactly this work and is now superseded.

## Capabilities

### New Capabilities
- `skill-distribution`: Which skills this repo ships under `.claude/skills/`, and how `install.sh` projects that set into `~/.claude/skills/` — symlinking every shipped skill and pruning links for skills the repo no longer ships, without disturbing links owned by other sources.

### Modified Capabilities
- `roadmap-planning`: Three requirement changes. (1) The frontmatter requirement tightens from "the description must not mention a refine-driven checkbox flip" to "the description must not name `arbor-auto-refine` at all," and re-baselines the version floor from `1.2` to `1.3`. (2) The human-invocation guardrail must convey "no other skill auto-invokes this one" while naming only surviving skills. (3) The change-scope requirement — which forbade deleting `arbor-auto-refine` and required its surviving references be left in place — is removed and replaced by requirements that mandate the deletion and a refine-free `arbor-auto-roadmap`.

## Impact

- **Files changed**: `.claude/skills/arbor-auto-refine/` (deleted, staged via `git rm -r`), `.claude/skills/arbor-auto-roadmap/SKILL.md` (scrubbed + version bump), and `install.sh` (**only** if the empirical prune check fails), plus these OpenSpec artifacts. No other path may appear in `git status`.
- **Explicitly out of scope**: `arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` are not modified. `docs/roadmaps/roadmap-native-workcycles.md` is read but left untouched — roadmap bookkeeping is handled by the caller outside this lifecycle.
- **Expected residue, not an oversight**: `arbor-auto-developer` still references `arbor-auto-refine` in nine places after this change (its `description`, the "agent 1" framing, the self-seed step, the blocked-issue triage note, and its guardrails). That is **expected and correct** — it is resolved by roadmap item R4, which rewrites developer wholesale. Half-fixing it here would leave developer describing a self-seed step it cannot perform while still carrying the GitHub backlog R4 removes. Other skills and this repo's git history also mention refine; only `arbor-auto-roadmap` is required to be clean.
- **Installed environments**: any machine that ran `install.sh` has a live `~/.claude/skills/arbor-auto-refine` symlink. After this change it dangles until `install.sh` is re-run, at which point the prune removes it. Scheduled refine runs configured via the `schedule` skill will fail to resolve the skill; that is the intended end state, and no migration tooling ships (parent roadmap non-goal).
- **Verification**: this repo has no build, no test suite, no `package.json`, and no gate command — the product is Markdown skill definitions plus `install.sh`. Verification is therefore expressed as concrete, greppable shell checks and one live `./install.sh` observation, each attached to its task.
