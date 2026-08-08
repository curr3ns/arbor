## Why

Roadmap item R1 redefined a checked roadmap box to mean "implemented, gated, and merged," and R2 deleted `arbor-auto-refine`, the only skill that ever flipped one. Nothing closes a roadmap item today: a work cycle can build R3 and merge it while the box stays unchecked forever. `arbor-auto-work` is the only place that holds the item reference, the branch, the gate outcome, and the commit at the same moment, so the flip belongs inside its commit — it then lands atomically on merge, needs no second bookkeeping push, has no push race to reconcile, and behaves identically for a scheduled agent and for a human running the skill by hand. This is roadmap item R3 of `docs/roadmaps/roadmap-native-workcycles.md`.

## What Changes

- Add an **optional** input token `roadmap:docs/roadmaps/<slug>.md#R<n>` to `arbor-auto-work`, documented in the **Inputs** section alongside the existing model tokens and mode flags. Its absence is the normal case for work that is not on a roadmap and is never an error.
- Extend step 0 to set the `roadmap:` token aside with the `spec:`/`work:`/`gate:`/`archive:` tokens and the `--interaction`/`--pr` flags, so it can never leak into the work description that becomes the work-ID slug in steps 2–3.
- Resolve and validate the reference **at step 0**, before a branch exists: a ref naming a file that is not present, an `R<n>` that is not in that file, or an item whose box is already checked is a **hard error that stops the run**. All three cases are called out by name. Nothing is silently ignored, and nothing is "best effort."
- Extend step 5 so that, **before the commit is made**, the referenced item's line is rewritten from `- [ ] **R<n>**` to `- [x] **R<n>**`, and — if no unchecked item remains anywhere in that file — the file is moved to `docs/roadmaps/archive/` with `git mv` so the flip and the archival land in the same commit as the work. `docs/roadmaps/archive/` does not exist in this repo yet, so the instruction creates it before the move.
- Add commit-body bullets: `- Roadmap: <slug> R<n> complete` whenever a ref was passed, plus `- Roadmap <slug> complete; archived` when that item was the last unchecked one in the file.
- Preserve the gate contract exactly: the flip lives inside step 5, which a genuine gate failure never reaches because step 4 already stops the cycle. No new text weakens that, and the flip is never performed as bookkeeping on a failed run.
- Preserve the environment-blocked contract: an environment-blocked stage still reaches step 5 and still flips, and still carries its existing visible trace bullet (`- E2E skipped: environment-blocked (<reason>); not independently verified.`) next to the roadmap bullet.
- Update the YAML frontmatter `description` to mention the new token, and bump `metadata.version` from `1.1`.
- Preserve the skill's structure and voice: steps stay numbered 0–7 with the same headings and the same meaning, and the existing sections stay. This threads one new concern through step 0, step 5, and **Inputs** — it is not a restructuring.

## Capabilities

### New Capabilities
- `work-cycle`: The `arbor-auto-work` skill's contract — the inputs it accepts and strips, the work-ID and branch conventions, its delegation of the OpenSpec lifecycle, and the commit/push/integrate steps. This change introduces the capability and specifies the roadmap-closing behavior within it; the pre-existing behavior is captured as the surrounding requirements it must not disturb.

### Modified Capabilities
- `roadmap-planning`: One requirement is retired. **Change scope is limited to refine deletion and the roadmap scrub** was written by the previous change (`dev-2-delete-auto-refine`) to fence that change's blast radius, and it states that `arbor-auto-work` SHALL NOT be modified. That fence has served its purpose and is now superseded — it is removed and replaced by this change's own scope requirement in `work-cycle`. This is spec bookkeeping only: no file under `.claude/skills/arbor-auto-roadmap/` changes, and no behavior of `arbor-auto-roadmap` changes.

## Impact

- **Files changed**: `.claude/skills/arbor-auto-work/SKILL.md` only, plus these OpenSpec artifacts. Nothing else in the repo may appear in `git status`.
- **Explicitly out of scope**: `arbor-opsx-auto` is **not** touched — it runs branch-local and leaves everything uncommitted, so it has no roadmap concern, and the parent roadmap names changing it as a non-goal. `arbor-auto-developer` (which will pass the new token) is rewritten by roadmap item R4, `arbor-project-scaffold` (which will create `docs/roadmaps/archive/`) by item R6, and `arbor-auto-roadmap` is already done at R1/R2. No new skill and no new file outside `openspec/changes/dev-3-workcycle-roadmap-close/` is created.
- **`docs/roadmaps/archive/` does not exist yet**: this change ships no directory and no `.gitkeep` — creating it is a step in the instruction the skill follows at the moment it first archives a roadmap. Materializing it here would be a file outside the declared scope, and R6 owns scaffolding it for new projects.
- **`docs/roadmaps/roadmap-native-workcycles.md`** is read for context and is **not** modified. R3's own checkbox is flipped outside this change — the skill being taught the trick cannot yet have been used to build itself.
- **Producer/consumer state after this change**: `arbor-auto-roadmap` already documents the `docs/roadmaps/<slug>.md#R<n>` format (R1), and this change makes `arbor-auto-work` its first consumer. No automated caller passes the token until R4, so until then it arrives only from a human invocation — which is exactly the hand-run path the acceptance criteria require to work.
- **Verification**: this is a skills repo — the product is Markdown skill definitions under `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, no `package.json`, and no gate command. Verification is reading the edited Markdown against the acceptance criteria, plus concrete greppable checks attached to each task.
- **Known pre-existing condition**: `openspec validate --all` reports "Spec must have a Purpose section" against the specs already in `openspec/specs/`. That predates this change and is not addressed here; the delta specs added here follow the same structure as the archived changes that produced those specs.
