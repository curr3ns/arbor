## 1. Frontmatter

- [x] 1.1 Rewrite the YAML frontmatter `description` in `.claude/skills/arbor-auto-developer/SKILL.md` so it describes only the rewritten behavior: reading `docs/roadmaps/*.md` as the work queue, selecting one item, dispatching one `arbor-auto-work` subagent, and merging to `main`. Verify: every behavior the description claims is one the body specifies, and the body specifies nothing substantial the description contradicts.
- [x] 1.2 Keep the scheduled/one-cycle-per-run framing in the `description` — run on a schedule (~hourly; the schedule skill's cron has a 1h minimum interval), each run a single cycle and not a loop. Verify: both the schedule cadence and the single-cycle claim appear in the description.
- [x] 1.3 Strip every removed concern from the `description`: no pull request, no review feedback, no issue backlog, no label, no integration branch, no self-seeding, and no `arbor-auto-refine`. Verify: `grep -n 'arbor-auto-refine\|pull request\|backlog\|priority:\|integration branch\|self-seed' .claude/skills/arbor-auto-developer/SKILL.md` returns no line inside the frontmatter block.
- [x] 1.4 Set `metadata.version` to `"2.0"`, replacing `"1.4"`. Verify: `grep -n 'version:' .claude/skills/arbor-auto-developer/SKILL.md` shows `version: "2.0"`, and the frontmatter still parses with `name`, `description`, `license`, and `metadata` present.

## 2. Framing and Setup

- [x] 2.1 Rewrite the opening framing paragraph so it states the skill's actual job: a scheduled burn-down agent that reads `docs/roadmaps/*.md` as its queue, works one item per run, and merges to `main`. Verify: the paragraph names no removed concept (agent numbering, refine, integration branch, running PR, issue queue) and reads as a complete statement that does not presuppose deleted text.
- [x] 2.2 State in the framing that each run is one cycle, that the skill does not loop internally, and that the `schedule` skill's cron cadence (~hourly, 1h minimum interval) provides the "keep polling". Verify: all three claims are present, and the cadence note names the 1h minimum.
- [x] 2.3 Remove the `gh auth status` setup step and the integration-branch setup step. Verify: `grep -nE 'gh auth|gh repo view|integration branch' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing, and `grep -nE '\bdevelop\b' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing — use the word-boundary form, since a bare `develop` substring matches the skill's own name `arbor-auto-developer` on nearly every line and is not evidence of a surviving integration branch.
- [x] 2.4 Decide Setup explicitly: drop the `## Setup (once, before the first scheduled run)` section entirely (per design D9), moving the skill's real precondition — that human-authored roadmaps exist under `docs/roadmaps/` — into the framing. Verify: no Setup heading remains, and no surviving sentence presents the absence of roadmaps as a setup failure.

## 3. Remove the backlog, the PR path, and refine

- [x] 3.1 Delete the entire P0/P1 PR-feedback path — the open-PR lookup, unresolved review threads, `CHANGES_REQUESTED`, `gh pr checks`, the feedback subagent, and the reply-and-resolve instruction. Verify: `grep -n 'gh pr\|pull request\|review thread\|review comment\|CHANGES_REQUESTED\|P0\|P1\|P2' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing.
- [x] 3.2 Delete the issue queue and everything that served it: `gh issue list`, the `agent:backlog` queue, all `priority:*` and `type:*` label requirements, the queue cap, the `Closes #N` trailer instruction, and the issue-comment failure record. Verify: `grep -n 'gh issue\|agent:backlog\|priority:\|type:\|Closes #\|issue' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing that refers to a GitHub issue.
- [x] 3.3 Delete the running-PR machinery: the "ensure the running PR exists" step and the "at most one open PR" guardrail. Verify: no instruction opens, updates, or reuses a pull request, and no guardrail caps a number of open PRs.
- [x] 3.4 Delete refine self-seeding and every mention of `arbor-auto-refine`, including the "never invoke refine more than once per run" guardrail and the "blocked issues wait for refine's triage" clause. Verify: `grep -n 'arbor-auto-refine' .claude/skills/arbor-auto-developer/SKILL.md` produces no output and exits non-zero.
- [x] 3.5 Read every part of the file that previously depended on removed content and confirm each reads as a complete, self-standing statement. Verify: no stub sentence, dangling conjunction, orphaned parenthetical, or claim missing its subject survives — specifically no "(see `arbor-auto-refine` for agent 1)"-style label and no "agent 2 of" numbering.

## 4. The cycle — read the queue

- [x] 4.1 Keep `## The cycle` with the directive `You MUST create a todo per step and complete them in order.` immediately under it, and renumber the steps to the new cycle. Verify: `grep -n 'You MUST create a todo per step and complete them in order' .claude/skills/arbor-auto-developer/SKILL.md` matches, under the cycle heading.
- [x] 4.2 Write the read step: each cycle reads the non-archived roadmap files `docs/roadmaps/*.md` as they stand on `main`. Verify: the glob and `main` both appear in that step, so the read is not against an arbitrary checked-out branch.
- [x] 4.3 State the archive exclusion explicitly — `docs/roadmaps/archive/` is not read — rather than leaving it implied by the single-level glob. Verify: the exclusion names `docs/roadmaps/archive/`, and no instruction anywhere directs a recursive search (`find`, `**/*.md`, `rg --files`) over `docs/roadmaps/`.

## 5. The cycle — select exactly one item

- [x] 5.1 Write the outer walk: roadmaps are considered in filename order, and selection happens within the first roadmap that holds an **eligible** item. Verify: the wording is "first roadmap holding an eligible item", not "first roadmap with an unchecked item".
- [x] 5.2 Write the inner walk: within that roadmap take the earliest incomplete phase, and within that phase the first unchecked item not carrying a blocked annotation. Verify: all three selectors (earliest incomplete phase, first unchecked, not blocked-annotated) are present and ordered.
- [x] 5.3 Define "earliest incomplete phase" concretely — phases are the `## Phase <k>: <name>` headings in file order, and a phase is incomplete when at least one item under it is unchecked, annotated or not. Verify: the definition states that a blocked item still counts toward its phase being incomplete.
- [x] 5.4 State the all-blocked-roadmap case: a roadmap whose only unchecked items are all blocked-annotated holds no eligible item, so the walk moves on to the next roadmap by filename instead of ending the run. Verify: the sentence exists and explicitly continues the walk rather than idling.
- [x] 5.5 State the blocked-earliest-phase case: an earliest incomplete phase whose unchecked items are all blocked does **not** fall through to a later phase in the same roadmap — phases are strictly sequential — so that roadmap yields nothing and the walk continues to the next file. Verify: the prohibition is written as a prohibition ("does not fall through"), not left as an omission, and the reason (strict sequencing) is given.
- [x] 5.6 State that exactly one item is selected per cycle. Verify: no instruction selects, batches, or queues more than one item.

## 6. The cycle — dispatch one subagent

- [x] 6.1 Write `## Subagent dispatch`: a fresh subagent with a self-contained prompt carrying the selected item's **full text** and its reference in the form `roadmap:docs/roadmaps/<slug>.md#R<n>`. Verify: the token form matches `arbor-auto-work`'s documented input exactly, and the prompt is described as self-contained rather than pointing at the roadmap.
- [x] 6.2 Instruct the subagent to run `arbor-auto-work` in autonomous mode — its default, no `--interaction`, no `--pr` — merging to `main`. Verify: "default", "no `--interaction`", "no `--pr`", and `main` all appear.
- [x] 6.3 Confirm no integration-target override survives from the old dispatch section: `main` is `arbor-auto-work`'s own default and nothing here overrides it. Verify: no sentence directs the subagent to branch off or merge into anything other than `main`.
- [x] 6.4 State the return contract: the subagent returns the compact result `{ outcome, work_id, branch, note }`. Verify: the four field names appear together in the dispatch section.
- [x] 6.5 State that exactly one subagent is in flight at a time and that the cycle waits for it before doing anything else. Verify: the wait is explicit, so a retry can only follow a finished attempt.

## 7. The cycle — idle, success, and completion

- [x] 7.1 Write the idle path: no eligible item anywhere ends the run quietly — no dispatch, no notification, no error, nothing to do until the next scheduled tick. Verify: all three suppressions (dispatch, notification, error) are named in that step.
- [x] 7.2 State that the absence of any roadmap file at all takes the same quiet path, and is not a setup failure, a misconfiguration, or an error. Verify: the no-roadmap case is addressed by name and routed to the same quiet exit.
- [x] 7.3 Write the success path: on `outcome` reporting a successful merge, confirm the merge landed on `main` and send the merge-landed notification. Verify: the step verifies the merge rather than assuming it, and it performs no roadmap edit of its own.
- [x] 7.4 Write the roadmap-complete observation: the merged item was the last unchecked one in its file, observable from the merged result (the file is gone from `docs/roadmaps/` and present under `docs/roadmaps/archive/`, and the work commit carries `- Roadmap <slug> complete; archived`). Verify: the step is phrased as an observation, and it states that `arbor-auto-work` performed the `git mv` inside its work commit.
- [x] 7.5 State that this skill never moves, copies, renames, or deletes a roadmap file, and never creates `docs/roadmaps/archive/`. Verify: `grep -n 'git mv\|mkdir' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing that directs this skill to perform the move.

## 8. The cycle — failure, retry, and the blocked annotation

- [x] 8.1 Write the retry path: on gate failure, dispatch exactly one retry subagent in a fresh context, passing the failure output. Verify: "one retry", "fresh context", and "failure output" all appear, and the retry is sequential to the first attempt.
- [x] 8.2 Forbid a third attempt on the same item in the same run, and forbid moving on to a different item after a blocked one in the same run. Verify: both prohibitions are stated, and neither is softened to a preference.
- [x] 8.3 Write the annotation: on a second failure, append `<!-- blocked: <reason> -->` to the **end** of the failed item's line, leaving the item's existing text byte-identical, and leaving its checkbox unchecked. Verify: the annotation form matches character for character, "end of the line" and "byte-identical" are both stated, and no instruction permits rewording, reflowing, re-wrapping, or renumbering the item or its continuation lines.
- [x] 8.4 Specify `<reason>` as a one-line summary of what broke at which gate step. Verify: both "one line" and the what-broke/which-step content are stated, so the reason is triageable without opening a log.
- [x] 8.5 State the purpose: the annotation is pushed to `main` as bookkeeping so later cycles skip the item and one bad item cannot stall the roadmap. Verify: the push target is `main`, the annotation is committed and pushed rather than left uncommitted or on a side branch, and the skip-in-later-cycles consequence is stated.
- [x] 8.6 Write the race procedure: if the push is rejected because `main` has moved, fetch and rebase — or re-pull and re-apply the annotation onto the current `main`. Verify: the moved-branch case is addressed explicitly rather than assuming a clean push.
- [x] 8.7 Require re-locating the item's line by its `**R<n>**` marker rather than by line number when re-applying. Verify: the by-marker instruction is present and explicitly rejects line-number addressing.
- [x] 8.8 Require re-checking, before re-pushing, that the item is still unchecked and still unannotated. Verify: both preconditions are named as re-checks, not as one-time checks from before the race.
- [x] 8.9 State the abandonment rule: if the item has since been checked, or has already been annotated by another actor, drop the annotation rather than force-push. Verify: both losing cases are named, "drop the annotation" is the stated outcome for each, and force-pushing `main` is forbidden by name.
- [x] 8.10 State that blocked items wait for a human — the skill invents no re-attempt or triage policy, and a human unblocks an item by fixing the cause and deleting the annotation. Verify: the human-in-the-loop expectation is visible rather than left as an unexplained dead end, and no automated re-attempt is described.

## 9. Notifications

- [x] 9.1 Write `## Notifications` with exactly three triggers: merge landed, item blocked after retry, and roadmap complete. Verify: exactly three are enumerated and no fourth trigger appears anywhere in the file.
- [x] 9.2 Preserve the notification form: `PushNotification`, one line, under 200 chars, leading with what's actionable. Verify: the tool name, the one-line rule, the 200-char limit, and the actionable-first rule are all present.
- [x] 9.3 State the two suppressions as rules: do not notify on dispatch, and do not notify on a quiet idle run. Verify: both are written as explicit rules rather than left as absences.
- [x] 9.4 State that merge-landed and roadmap-complete both fire when the merged item was the last one, with neither replacing the other. Verify: the co-occurrence is explicit.
- [x] 9.5 State the degradation rule: if `PushNotification` is unavailable, continue without failing the run. Verify: the fallback is present and the durable records it relies on (the merge on `main`, the annotation, the archived file) are named rather than pointing at removed artifacts like an issue comment or a resolved review thread.

## 10. Guardrails

- [x] 10.1 Keep the strictly-sequential phase rule: never a later phase while an earlier one still has an unchecked item. Verify: present in `## Guardrails` and stated as a prohibition.
- [x] 10.2 Keep the one-subagent-at-a-time rule: exactly one subagent in flight, never two. Verify: present in `## Guardrails` with "never two" or equivalent force.
- [x] 10.3 Keep the two-attempt ceiling (one original plus one retry) on the same item in a run. Verify: present, and its wording refers to a roadmap item rather than an issue.
- [x] 10.4 Keep "one run = one cycle; do not loop internally; exit when done or idle and let the scheduler bring you back". Verify: present and unweakened.
- [x] 10.5 Keep the repo-scoped identity rule — only ever touch this repo, under the maintainer's own identity, no cross-repo activity — rewritten so it names only artifacts the skill still uses (branches and roadmap files, not issues or PRs). Verify: present, and it references no removed artifact type.
- [x] 10.6 Rewrite the never-touch-roadmap-content guardrail as an enumeration: never write an item's text, never add/remove/rename a phase, never flip a checkbox in either direction, and never invoke `arbor-auto-roadmap`. Verify: all four prohibitions appear by name.
- [x] 10.7 State that the checkbox flip belongs to `arbor-auto-work` inside its work commit, and that this skill does not flip one even when it observes a merge that should have. Verify: the attribution is explicit and no "help out" exception is granted.
- [x] 10.8 Carve out the annotation explicitly: it is the single write this skill makes to a roadmap file, and it is **bookkeeping about an item, not authorship of one**. Verify: the bookkeeping/authorship distinction is written in those terms, adjacent to the authorship prohibition, so it cannot be read as a general licence to write.

## 11. Scope discipline

- [x] 11.1 Confirm no `--goal` flag, foreground mode, or internal multi-item loop was added — that is R5. Verify: `grep -n -- '--goal\|foreground' .claude/skills/arbor-auto-developer/SKILL.md` returns nothing, and the skill works exactly one item per invocation.
- [x] 11.2 Confirm the working tree changes nothing outside `.claude/skills/arbor-auto-developer/SKILL.md` and `openspec/`. Verify: `git status --porcelain` lists no other path, and specifically no path under `.claude/skills/arbor-auto-work/`, `.claude/skills/arbor-auto-roadmap/`, `.claude/skills/arbor-opsx-auto/`, or `.claude/skills/arbor-project-scaffold/`, and no new skill directory.
- [x] 11.3 Confirm no `docs/roadmaps/archive/` directory, placeholder, or `.gitkeep` was created. Verify: the path does not appear in `git status --porcelain` and does not exist in the working tree.
- [x] 11.4 Confirm `docs/roadmaps/roadmap-native-workcycles.md` is untouched — R4's own checkbox is flipped outside this change, by `arbor-auto-work`'s commit step. Verify: it does not appear in `git status --porcelain`.

## 12. Final verification

- [x] 12.1 Run the removal sweep over the finished file and require zero hits: `grep -nE 'arbor-auto-refine|agent:backlog|priority:|gh auth|gh issue|gh pr|pull request|integration branch|review thread|CHANGES_REQUESTED|Closes #|--goal' .claude/skills/arbor-auto-developer/SKILL.md`. Verify: no output. Note the sweep deliberately omits `--pr`: task 6.2 requires the dispatch section to state that neither `--interaction` nor `--pr` is passed, so the flag name appears exactly once, as a prohibition on passing it. Separately confirm that is its only occurrence: `grep -c -- '--pr' .claude/skills/arbor-auto-developer/SKILL.md` returns 1.
- [x] 12.2 Run the retention sweep and require a hit for each: `You MUST create a todo per step`, `docs/roadmaps/*.md`, `docs/roadmaps/archive/`, `roadmap:docs/roadmaps/<slug>.md#R<n>`, `<!-- blocked:`, `{ outcome, work_id, branch, note }`, `PushNotification`, `main`, `**R<n>**`. Verify: every string is present at least once.
- [x] 12.3 Read the finished `SKILL.md` end to end against every requirement in `specs/roadmap-queue/spec.md`, checking each scenario literally rather than approximately. Verify: every scenario holds when read as written, with particular attention to the two walk edge cases (all-blocked roadmap continues the walk; all-blocked earliest phase does not fall through) and the three race outcomes (re-apply, drop on checked, drop on already-annotated).
- [x] 12.4 Read the finished file for internal consistency: the frontmatter description, the framing, the cycle steps, the dispatch section, the notifications, and the guardrails must all describe the same skill, with no rule stated in one place and contradicted in another. Verify: no surviving sentence describes behavior the rewrite removed, and no section presupposes text that is no longer in the file.
