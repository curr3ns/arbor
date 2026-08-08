## Context

This is a skills repo: the product is Markdown skill definitions at `.claude/skills/<name>/SKILL.md`, plus `install.sh`, which symlinks each skill directory into `~/.claude/skills/`. There is no `package.json`, no build, no test suite, and no gate command. "Implementation" here means deleting one directory, rewriting five sentences in another file, and running one shell script; "verification" means greppable shell checks and one live observation.

`.claude/skills/arbor-auto-refine/SKILL.md` (v1.3, 186 lines) is agent 1 of the old two-agent continuous dev loop. It audits docs, explores the running app, triages blocked issues, files GitHub backlog issues, and — the part that now breaks — **flips a roadmap item's checkbox the moment it files that item's issue**, then archives the roadmap file or closes the Milestone when the last box goes. It also still reads the singular `docs/roadmap/` path that R1 renamed away.

`.claude/skills/arbor-auto-roadmap/SKILL.md` (v1.3, 101 lines) was rewritten by R1 into a files-only planning skill and now documents a checked box as "implemented, gated, and merged." R1 deliberately did **not** scrub refine's name from it — design decision D3 of `openspec/changes/archive/2026-08-07-dev-1-roadmap-files-only/design.md` reasoned that a skill denying the existence of a skill that is still installed and still running on a timer is worse than a stale reference, and deferred the scrub to R2 so the deletion and the scrub land together. Five references survive:

| Line | Text | Problem |
| --- | --- | --- |
| 3 | frontmatter `description`: "neither arbor-auto-refine nor arbor-auto-developer ever invoke it automatically" | names a skill that will not exist; `description` is routing text |
| 12–19 | "Companion to `arbor-auto-refine` (agent 1) and `arbor-auto-developer` (agent 2) in the continuous dev loop… The other two skills poll what it produces" | the two-agent loop is being dismantled; "the other two" is wrong once refine is gone |
| 31–33 | non-goals rationale: "keeps `arbor-auto-refine` from later expanding scope back into something the user deliberately excluded" | the rationale for asking about non-goals is loadbearing; only its justification depends on refine |
| 39–41 | item sizing: "the same sizing `arbor-auto-refine` already uses when it files issues" | appeals to refine's issue-filing behavior as the sizing authority |
| 100 | guardrail: "Neither `arbor-auto-refine` nor `arbor-auto-developer` ever invoke this skill automatically" | the *claim* must survive; only the roster is wrong |

The parent roadmap's R2 (`docs/roadmaps/roadmap-native-workcycles.md`) is the authority for why this happens now: under R1's semantics a refine pass marks unimplemented work as done, so refine must go in the phase that redefined the checkbox.

## Goals / Non-Goals

**Goals:**

- `.claude/skills/arbor-auto-refine/` gone from the repo, with the deletion **staged in git** (`git rm -r`), not merely absent from the working tree.
- `install.sh`'s existing prune loop confirmed to handle the removal **by observation**, not by reading — and fixed if and only if the observation fails.
- Zero occurrences of `arbor-auto-refine` in `.claude/skills/arbor-auto-roadmap/SKILL.md`, with every replacement reading as though refine never existed.
- `metadata.version` in `arbor-auto-roadmap` bumped above `1.3`.
- R1's now-superseded spec requirements retired explicitly rather than silently contradicted.

**Non-Goals:**

- **Replacing anything refine did.** Its static doc audit, dynamic app exploration, and blocked-issue triage are dropped, not relocated. After this change no agent finds bugs. That is the parent roadmap's stated non-goal, not an omission.
- **Touching `arbor-auto-developer`.** It references refine in nine places and keeps every one of them. See D5.
- **Touching `arbor-auto-work`, `arbor-opsx-auto`, or `arbor-project-scaffold`.**
- **Touching `docs/roadmaps/roadmap-native-workcycles.md`.** Read for context; its R2 checkbox is bookkeeping handled outside this lifecycle.
- **Scrubbing refine from anywhere else.** Other skills, archived OpenSpec changes, and git history mention refine. All fine, all out of scope.
- **Migration tooling** for downstream repos or for scheduled refine cron entries. Hand-handled, per the parent roadmap's non-goals.
- **Restructuring `arbor-auto-roadmap`.** Only the five references change (plus the version). The interrogation, template, item-reference section, and every other guardrail stay exactly as R1 left them.

## Decisions

**D1 — `git rm -r`, not `rm -rf`.**
The deletion is staged in the index, so `git status --porcelain` shows a `D` for every file under the directory and the change is visible to any later `git diff --cached` or commit taken by the caller. A filesystem `rm` leaves the same working tree but an unstaged deletion, which is easy for a subsequent partial `git add <path>` to miss — and this change's whole point is that the skill stops shipping. Alternative considered: `git rm -r --cached` plus filesystem removal — rejected, it is the same thing with more steps. The directory holds exactly one file (`SKILL.md`), so `git rm -r .claude/skills/arbor-auto-refine` is a single unambiguous command.

**D2 — The `install.sh` confirmation is an experiment, not a code review.**
`install.sh` ends with a prune loop that removes `~/.claude/skills/*` symlinks that (a) are symlinks, (b) point into `$REPO_DIR/.claude/skills/`, and (c) are dangling. Reading it, it clearly should remove `arbor-auto-refine`. Reading is not enough, for three reasons that only a run can settle: the installed link's `readlink` value carries a **trailing slash** (`.../arbor-auto-refine/`) because the install loop globs `*/`, so the `case` pattern match is a real question; `[ -e "$dst" ]` on a symlink to a deleted directory depends on `-e` following the link (it does, but that is the exact assumption under test); and the loop must not take out the eleven *surviving* arbor links in `~/.claude/skills/`. So the acceptance criterion is a before/after observation: capture the link inventory, delete the directory, run `./install.sh`, and assert both the removal and the survivors. Running `./install.sh` is idempotent and pre-approved in this repo.
**Expected side effect, not a regression:** `~/.claude/skills/` currently holds 12 links while the repo ships 16 skills — the four `openspec-*` skills have never been installed on this machine. Running `./install.sh` will create links for them. That is install.sh doing its documented job (link everything the repo ships), so the post-run assertion checks *removal of refine* and *survival of the other eleven arbor links*, and treats newly added links for shipped skills as expected rather than as damage.
**Contingency:** if the prune does not fire, fix `install.sh` — most likely by normalizing the trailing slash (link `"${skill_dir%/}"` instead of `"$skill_dir"`, or strip it before the `case`) or by testing `[ -L "$dst" ] && [ ! -e "$dst" ]` explicitly. `install.sh` is otherwise untouched; no refactor rides along.

**D3 — Five considered rewrites, each with its own replacement rationale.**
A blind delete of each sentence would leave stubs ("Companion to  (agent 2)…") or drop real rules. Each reference is rewritten to say something true and self-supporting:

- **Frontmatter `description` (line 3).** Keep the "purely user-invoked, not on a timer" claim; drop the two-skill roster. It becomes a claim about *no* other skill invoking it, which is stronger and does not go stale when R4 rewrites developer.
- **Opening framing (lines 12–19).** Becomes the post-refine world: this skill is the human-invoked planning front end; `arbor-auto-developer` reads `docs/roadmaps/*.md` directly as its work queue and `arbor-auto-work` builds an item and closes its box. Refine is not mentioned; "the other two skills poll what it produces" is replaced by naming the actual consumers. The preserved substance: this skill is not part of the loop's cadence, is never invoked by the loop, polls nothing, and never flips a box.
- **Non-goals rationale (lines 31–33).** New rationale that stands alone: non-goals are what keeps a later planning pass — or a reader of the roadmap — from quietly re-expanding scope into something the user ruled out, and they are the only place that exclusion is written down. This does not depend on any agent existing.
- **Item sizing (lines 39–41).** New rationale that stands alone: an item is sized to a single OpenSpec change because one item becomes one `arbor-auto-work` cycle — one branch, one gate, one merge; an item too big to phrase that way becomes two items. This is *more* accurate than the old appeal to refine's issue sizing, since `arbor-auto-work` is now the actual consumer.
- **Guardrail (line 100).** Survives in spirit with a corrected roster: no other skill ever invokes this one automatically; it is only ever run by a human. Naming zero skills is deliberate — a roster is exactly what went stale here.

**D4 — Describe `arbor-auto-developer` as reading `docs/roadmaps/*.md`, even though R4 has not shipped.**
The rewritten framing states the consumer relationship as the roadmap defines it (R4), not as developer implements it today (a GitHub `agent:backlog` queue). Alternatives considered: (a) describe developer's *current* backlog behavior — rejected, it documents a queue this very roadmap is deleting and would need rewriting again in two items; (b) name no consumer at all — rejected, the item-reference format is only meaningful if the reader knows who consumes it. The forward reference is safe because `arbor-auto-roadmap` never invokes developer and never reads its state; the sentence is orientation for a human, not a contract. **Explicitly: `arbor-auto-developer` itself is not modified here.**

**D5 — Leave `arbor-auto-developer`'s nine refine references alone, and say so out loud.**
After this change `arbor-auto-developer` still names `arbor-auto-refine` in its `description`, its "agent 1" framing, its self-seed step, its blocked-issue note, and its guardrails. **This is expected and correct, not an oversight.** R4 rewrites developer wholesale — removing the backlog queue, the labels, the cap, the running PR, the PR-feedback path, and refine self-seeding together. Half-fixing it here would produce a skill that has lost its self-seed step but still polls a GitHub queue nobody fills, which is strictly worse than a skill that is coherently obsolete. Recorded here so a later reader does not file it as a miss. Only `arbor-auto-roadmap` is required to be refine-free by this change.

**D6 — Version `1.3` → `1.4`.**
The repo's convention is minor steps (`1.0`→`1.2`→`1.3`). Alternative considered: `2.0`, since scrubbing a companion skill from the description is user-visible. Rejected — nothing consumes `metadata.version` as a compatibility signal, and R1's own bump for a far larger rewrite was a minor step. Consistency wins.

**D7 — `install.sh`'s behavior becomes its own capability, `skill-distribution`.**
The prune contract is not roadmap planning, so folding it into `roadmap-planning` would put an unrelated requirement in a spec named for the roadmap skill. `skill-distribution` covers what the repo ships under `.claude/skills/` and how `install.sh` projects that set into `~/.claude/skills/`. It is the natural home for both "refine is no longer shipped" and "removing a shipped skill removes its installed link," and it will absorb R6's scaffolding-adjacent install concerns later if any arise.

**D8 — Retire R1's scope requirement explicitly rather than contradict it.**
`openspec/specs/roadmap-planning/spec.md` currently carries `Requirement: Change scope is limited to the roadmap skill`, which states that `arbor-auto-refine` SHALL NOT be deleted and that surviving refine references SHALL be left in place — the exact opposite of this change. It is REMOVED with a reason and migration note, and replaced by ADDED requirements that mandate the deletion and the refine-free body. Alternative considered: MODIFY it in place — rejected, its name ("limited to the roadmap skill") is no longer true once `install.sh` is in the allowed-change set and a second skill is deleted, and a MODIFIED block inheriting a wrong title is worse than a clean removal plus replacement. Two further requirements *are* modified in place, because their subject is unchanged and only their content tightens: the frontmatter requirement (no refine mention at all; version floor re-baselined from `1.2` to `1.3`) and the never-flips/human-invoked requirement (the guardrail must name only surviving skills).

**D9 — Verification is greppable shell, one check per task.**
With no gate command, "done" has to be mechanically checkable by a later agent with no context. Every task carries an explicit `Verify:` clause that is a command plus its expected result (`grep -c` returning 0, `ls` not listing a name, `git status --porcelain` showing exactly the expected paths, `readlink` on each surviving link). The one non-grep check — the `install.sh` observation — is written as an explicit before/after procedure so it cannot be satisfied by reading the script.

## Risks / Trade-offs

- **The prune loop does not actually remove the link (trailing-slash `case` mismatch, or `-e` semantics)** → Caught by design: the criterion is an observation, and D2 names the two likely fixes. `install.sh` is in the allowed-change set precisely for this branch.
- **`./install.sh` damages links in `~/.claude/skills/`** → The post-run assertion checks every surviving link individually (name present, still a symlink, still resolving into this repo), not just that refine's is gone. `install.sh` only removes links that both point into this repo's skills dir and dangle, so non-arbor links (`openspec-*`) are structurally out of reach; the check verifies that rather than assuming it.
- **Machines that do not re-run `install.sh` keep a dangling `~/.claude/skills/arbor-auto-refine`, and any refine cron entry starts failing** → Accepted and intended. A refine run that *succeeded* would mark unbuilt work as done, so a hard failure is the strictly better outcome. No migration tooling ships (parent roadmap non-goal); cron entries are removed by hand.
- **Rewriting five sentences risks quietly dropping a rule (especially line 100's guardrail)** → Mitigated by making each rewrite its own task with a "what must survive" clause, plus a final read-back task that diffs the file and confirms only the five references plus the version changed.
- **The new framing describes `arbor-auto-developer` behavior that does not exist yet** → Accepted per D4, bounded to two roadmap items, and harmless because no control flow depends on it.
- **Deleting 186 lines of skill is irreversible in the working tree** → Git history retains the file; rollback is `git restore --staged --worktree .claude/skills/arbor-auto-refine`. The parent roadmap explicitly rules out ever bringing back a GitHub-backed backlog, so there is nothing to preserve compatibility with.
- **`arbor-auto-roadmap` will describe a coherent world while `arbor-auto-developer` describes the old one** → Accepted per D5; the window closes at R4. The asymmetry is deliberate: roadmap is the skill a human invokes to plan, so its prose is what a human reads first.

## Migration Plan

Branch-local and uncommitted; the caller owns commits. Order matters only in one place: delete the directory **before** running `./install.sh`, or the prune has nothing to prune. Sequence: (1) capture the pre-state of `~/.claude/skills/`, (2) `git rm -r` the skill, (3) run `./install.sh` and assert the prune plus the survivors, fixing `install.sh` only on failure, (4) rewrite the five references and bump the version in `arbor-auto-roadmap`, (5) run the scope and grep checks. Rollback for the deletion is `git restore --staged --worktree .claude/skills/arbor-auto-refine` followed by `./install.sh` to restore the link; rollback for the scrub is `git checkout -- .claude/skills/arbor-auto-roadmap/SKILL.md`.

## Open Questions

None blocking. The only genuinely unknown outcome — whether the prune loop fires — is resolved by running the experiment, and both branches of that outcome have a defined action (D2).
