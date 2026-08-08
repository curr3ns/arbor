## Context

This is a skills repo: the product is Markdown skill definitions at `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, no `package.json`, and no gate command. "Implementation" here means rewriting one Markdown file, and the bar is prose precise enough that a future agent following it literally does the right thing in every case the acceptance criteria name. Verification is reading the finished file back against those criteria, plus greppable checks.

`.claude/skills/arbor-auto-developer/SKILL.md` (v1.4, 157 lines) is the scheduled burn-down agent. Its shape today:

- **Frontmatter** — a description built entirely around the PR-feedback path, the issue backlog, and refine self-seeding.
- **Setup (once, before the first scheduled run)** — three steps: `gh auth status` + repo name; pick an integration branch distinct from the default branch and confirm it exists; confirm `arbor-auto-work` is present.
- **The cycle** — a `You MUST create a todo per step and complete them in order.` directive, then: (1) check the integration branch's PR for P0 unresolved review threads and P1 failing CI; (2) the P0/P1 path — one subagent addresses feedback, replies to and resolves threads, notifies, ends the run; (3) the P2 issue-queue path — list open issues, self-seed with one `arbor-auto-refine` pass if empty, sort by `priority:*` label, pick the top one, dispatch one subagent, verify the merge, ensure the running PR exists, notify; on gate failure retry once then comment on the issue and notify blocked.
- **Subagent dispatch** — run `arbor-auto-work` autonomously, override the integration branch, add a `Closes #N` trailer, return `{ outcome, work_id, branch, note }`.
- **Notifications** — three triggers (merge landed, feedback addressed, issue blocked), one line, under 200 chars, actionable-first; don't notify on dispatch; degrade gracefully if unavailable.
- **Guardrails** — sequential subagents; never invoke refine twice; never merge to the default branch; at most one open PR; never touch roadmap content; P0/P1 beats the queue; max two attempts; one run = one cycle; repo-scoped under the maintainer's identity.

Roughly two thirds of that is now dead. R1 made roadmaps files-only and defined the item reference `docs/roadmaps/<slug>.md#R<n>`. R2 deleted `arbor-auto-refine` — and R2's own acceptance criteria explicitly noted that `arbor-auto-developer` would still name it afterwards, deferring the fix to here. R3 taught `arbor-auto-work` to flip the referenced box, archive a fully-checked roadmap with `git mv`, and record both in its commit body. So this file is the last place in the repo that still believes in the issue backlog.

The rewrite therefore is not a threading of one new concern through an existing prompt (which is what R3 was); it is a replacement of the selection input, the integration target, and the failure-bookkeeping mechanism, keeping the scheduling shape. That is why the version goes to `2.0` rather than `1.5`.

## Goals / Non-Goals

**Goals:**

- One skill file that reads `docs/roadmaps/*.md` as the queue and merges to `main`.
- A selection walk specified precisely enough that the two ambiguous cases (all-blocked roadmap; all-blocked earliest phase) resolve one way only.
- Exactly one `arbor-auto-work` subagent per cycle, autonomous, carrying the item text and the `roadmap:` ref.
- A quiet idle path for both "no eligible item" and "no roadmap files at all."
- One retry on gate failure, then a race-aware `<!-- blocked: <reason> -->` annotation pushed to `main`.
- Three notification events and no others.
- The surviving guardrails (strictly sequential phases, one subagent at a time, one cycle per run, repo-scoped identity, never authors roadmap content) intact and explicit.
- New frontmatter `description`; `metadata.version` `1.4` → `2.0`.

**Non-Goals:**

- **Adding `--goal`.** R5 owns the foreground mode. The default here stays one cycle per invocation, and nothing written now may presuppose a loop mode.
- **Touching `arbor-auto-work`, `arbor-auto-roadmap`, `arbor-opsx-auto`, or `arbor-project-scaffold`.** The flip, the archival, and the roadmap format are already correct upstream; this skill consumes them.
- **Creating `docs/roadmaps/archive/` or a `.gitkeep`.** R6 owns scaffolding it; `arbor-auto-work` creates it on demand.
- **Flipping R4's own box** in `docs/roadmaps/roadmap-native-workcycles.md`. That happens outside this change, in `arbor-auto-work`'s commit step.
- **Preserving any part of the PR-feedback path** "just in case." It is deleted, not commented out, not softened into an optional branch.
- **Inventing a triage path for blocked items.** Blocked items wait for a human. Nothing in this system re-attempts them automatically, and the skill must not imply otherwise.

## Decisions

**D1 — A full rewrite of the file, not an edit of the existing steps.**
Every input to the cycle changes: the queue (issues → roadmap files), the ordering key (`priority:*` label → filename, then phase, then position in phase), the integration target (integration branch → `main`), the failure record (issue comment → in-file annotation), and the seeding behavior (refine pass → nothing). Steps 1 and 2 disappear outright and step 3's six substeps are all replaced. Editing that in place would leave a file whose numbering, cross-references, and framing sentences were designed for a structure that no longer exists — the classic way a rewrite ends up carrying a scar. Alternative considered: minimal diff to keep review small. Rejected: the review surface here is "read the finished file against the criteria," which a coherent rewrite serves better than a small diff over an incoherent skeleton.

The one thing deliberately conserved is the *shape*: the frontmatter block, the `# Arbor auto-developer agent` heading, a framing paragraph, a numbered cycle under `## The cycle` carrying the `You MUST create a todo per step and complete them in order.` directive, a `## Subagent dispatch` section, a `## Notifications` section, and a `## Guardrails` bullet list. An agent that has read this skill before should still recognize it.

**D2 — Selection is specified as an explicit two-level walk with a named tie-break, and both degenerate cases are stated.**
The criterion "walks roadmaps in filename order, and within the first roadmap holding an eligible item picks the earliest incomplete phase and that phase's first unchecked item not carrying a blocked annotation" contains a subtlety that a natural reading gets wrong. "The first roadmap" is not "the first roadmap with any unchecked item" — it is the first roadmap holding an *eligible* item, where eligible means unchecked **and** unannotated **and** in that roadmap's earliest incomplete phase. Two cases must therefore be written out rather than left to inference:

1. A roadmap whose only unchecked items are all blocked-annotated holds no eligible item. The walk does not stop there and idle; it moves to the next roadmap by filename.
2. Within a roadmap, if the earliest incomplete phase's unchecked items are all blocked-annotated, the walk does **not** fall through to a later phase in the same file. Phases are strictly sequential — that is `arbor-auto-roadmap`'s guardrail and it survives here. That roadmap yields nothing and the walk continues to the next file.

Case 2 is the one an agent optimizing for "find something to do" will get wrong, because falling through looks helpful. It is not: a later phase's items were sequenced after an earlier phase's for a reason, and building them out of order is exactly the failure the strictly-sequential rule exists to prevent. The correct behavior is that a stuck phase blocks its own roadmap and only its own roadmap — other roadmaps keep moving, which is what stops one bad item from stalling *everything* while still honoring sequence within a file.

"Earliest incomplete phase" is defined concretely: phases are `## Phase <k>: <name>` headings in file order, and a phase is incomplete when at least one item under it is unchecked — annotated or not. The annotation affects *eligibility*, never *completeness*: a blocked item is still unchecked, so its phase is still incomplete and later phases stay closed. Alternative considered: treat a blocked item as complete for phase-sequencing purposes so the roadmap can keep flowing. Rejected — it would silently reorder a human's sequencing decision on the strength of a gate failure, and it would let the roadmap "finish" with unbuilt items.

**D3 — Non-archived means the top-level glob only, stated as an exclusion.**
The queue is `docs/roadmaps/*.md` on `main`. `docs/roadmaps/archive/*.md` is out. A single-level glob already excludes a subdirectory, but the exclusion is stated anyway because agents habitually reach for recursive search (`find`, `rg --files`, `**/*.md`) when told to "read the roadmaps," and a recursive read would resurrect completed roadmaps as an infinite supply of already-done work. Reading on `main` (not on whatever branch is checked out) is likewise stated: a stale local branch would re-select an item another cycle already merged.

**D4 — The blocked annotation is an HTML comment appended to the end of the item's line.**
`<!-- blocked: <reason> -->` renders as nothing in Markdown, so a human reading the roadmap sees the item unchanged; it lives on the item's own line, so it travels with the item through edits and re-orderings; and it is trivially greppable for both the skill's own eligibility check and a human's audit. Appending to the *end* of the line, leaving the existing text byte-identical, is required for the same reason R3 scoped its flip to the marker: the annotation must not become cover for rewording a human's roadmap item. The reason string is a one-line summary of what broke at which gate step — enough for a human to triage without opening a log, short enough to keep the line readable.

Alternatives considered: a separate `docs/roadmaps/blocked.md` ledger (needs its own reconciliation with item renumbering and drops, and splits the item's state across two files); flipping the box to a third state like `- [!]` (breaks `arbor-auto-work`'s validation, which requires `- [ ] **R<n>**`, and breaks the "no unchecked item remains" archival test); a GitHub issue (reintroduces the queue this change deletes).

**D5 — The annotation push is the one write, and it must be race-aware and idempotent-or-abandoned.**
Everything else this skill does is a read plus a subagent dispatch; the subagent owns all the writing. The annotation is the single exception, and it is a direct push to `main` outside the work branch, so `main` can move between the read and the push — another cycle's merge, a human's commit, a concurrent roadmap edit. The skill must therefore, on a rejected push: fetch and rebase (or re-pull) onto the current `main`, re-locate the item by its `**R<n>**` marker rather than by line number (the line number is the first thing a concurrent edit invalidates), and re-check the two preconditions — still unchecked, still unannotated — before pushing again.

The abandonment rule matters as much as the retry: if the item has since been checked, or has already been annotated by another actor, the skill drops the annotation rather than force-pushing. A checked box means someone (or some other cycle) actually built it, and re-annotating would slander landed work; an existing annotation already achieves the goal. Force-pushing `main` to win a race over a bookkeeping comment is never proportionate, and forbidding it explicitly is necessary because "make sure the annotation lands" reads as a licence to insist.

**D6 — This skill only observes roadmap completion; `arbor-auto-work` performs the archival.**
R3 put the `git mv` into `docs/roadmaps/archive/` inside the work commit, so by the time the merge lands the file has already moved. This skill must not also try to move it — a second `git mv` would fail, and worse, a skill that both observes and moves invites an implementation that races its own subagent. "Roadmap complete" is therefore an *observation* made after the merge: the item just merged was the last unchecked one in its file. The most robust way to observe it, and the one the skill should state, is to look at the merged result — the roadmap file is gone from `docs/roadmaps/` and present under `docs/roadmaps/archive/`, and `arbor-auto-work`'s commit body carries the `- Roadmap <slug> complete; archived` bullet. Both signals come from the subagent's own commit, so there is no independent computation to get wrong.

**D7 — Exactly three notifications, enumerated, with the two suppressions stated as rules.**
Merge landed, item blocked after retry, roadmap complete. The two suppressions — no notification on dispatch, no notification on a quiet idle run — are stated as their own rules rather than left as absences, because an agent that has just decided "there is nothing to do" feels an urge to report that, and an hourly cron reporting "nothing to do" 24 times a day trains the operator to ignore the channel, which then also loses the blocked notification. The idle run is silent precisely so the three real events stay legible. The existing constraints carry over verbatim: one line, under 200 chars, leading with what's actionable; and if `PushNotification` is unavailable, continue without failing the run — the merge, the annotation, and the archived file are all durable records on `main` regardless.

Roadmap complete and merge landed can both be true of the same cycle. They are separate events and both fire; nothing here says one replaces the other.

**D8 — Two attempts maximum, then bookkeeping, then stop.**
Original plus one retry in a fresh context carrying the failure output — the same budget the file has today, kept because it is the right one: one retry catches the transient and the shallow mistake, a third attempt on unchanged inputs is a loop. After the second failure the skill annotates and stops; it does not move on to the next eligible item in the same run, because one run is one cycle and the next tick is minutes-to-an-hour away. The retry counts as the cycle's one subagent slot being reused sequentially, never a second concurrent subagent.

**D9 — Setup shrinks to nothing and the section is dropped.**
Its three steps were: `gh auth status` (needed only for the issue queue and PRs — gone), pick and verify an integration branch (gone), confirm `arbor-auto-work` is present. The third is the only survivor and it is not setup — it is a precondition of the very first step of every cycle, and a skill that dispatches a subagent to run a missing skill discovers that immediately and loudly. Keeping a one-item "Setup (once, before the first scheduled run)" section for it would leave a heading whose title over-promises and whose content is a truism. The section is therefore removed, and the framing paragraph states the skill's actual precondition — that `docs/roadmaps/*.md` exists and is human-authored — where a reader will actually use it. Alternative considered: keep the section with the roadmap-existence check in it. Rejected: the absence of roadmaps is not a setup failure, it is a quiet idle run (criterion 4), and putting it under Setup would push an agent toward erroring instead of exiting quietly.

**D10 — "Never authors roadmap content" is restated with the annotation carved out explicitly.**
The skill acquires write access to a roadmap file for the first time, and the old guardrail's wording ("never touch roadmap content in any form") would be literally violated by the annotation. Deleting the guardrail is wrong; weakening it to "mostly doesn't" is worse. The correct wording enumerates what authorship means — writing items, writing phases, flipping checkboxes, invoking `arbor-auto-roadmap` — forbids all of it, and then names the annotation as the single permitted write, classified as bookkeeping about an item rather than a statement of what the item is. The distinction must be explicit in the text (criterion 8), because an agent that has been granted one write to a file will otherwise generalize.

The checkbox flip belongs to `arbor-auto-work` inside its work commit; this skill never flips one, not even to "help" when it observes a merge that should have flipped one. If a merge lands with an unflipped box, that is an upstream bug in the work cycle, not something to paper over here.

**D11 — The dispatch prompt is self-contained and passes the item text verbatim plus the ref.**
A fresh subagent shares no context with this cycle, so the prompt must carry the item's full text (the "why + acceptance criteria" that `arbor-auto-roadmap` requires each item to be phrased as) rather than a pointer to it, and the `roadmap:docs/roadmaps/<slug>.md#R<n>` reference so `arbor-auto-work` can validate and later flip it. Mode is autonomous — stated as "its default: no `--interaction`, no `--pr`" — and the integration target is `main`, which is `arbor-auto-work`'s own default, so unlike the old file there is **no override instruction**. Saying so plainly matters: the previous version's most distinctive dispatch instruction was an integration-branch override, and any residue of it would send merges somewhere other than `main`.

The return contract `{ outcome, work_id, branch, note }` is preserved verbatim, and the dispatch section states it, because the cycle's success/failure/blocked branching reads `outcome` and its notifications quote `work_id` and `branch`.

**D12 — Version `2.0`, and a description that describes only the surviving behavior.**
The repo has otherwise moved skills in minor steps (`arbor-auto-roadmap` 1.2 → 1.3 → 1.4, `arbor-auto-work` 1.1 → 1.2), each of which threaded one concern through an existing structure. This replaces the queue, the integration target, and the failure path, and removes two of the file's five sections; `2.0` is the honest signal even though nothing machine-reads the field. The `description` is routing text — it is what another agent or a scheduler reads to decide whether this skill is the right one — so every clause about PR feedback, the issue backlog, and refine self-seeding must go, and the scheduled/one-cycle-per-run framing must stay, since that is the operational fact a scheduler needs. It must also not name `arbor-auto-refine`, which is both a correctness requirement and the last cleanup R2 deferred.

## Risks / Trade-offs

- **The walk falls through to a later phase when the earliest incomplete phase is entirely blocked** → Mitigated by D2: the case is written out as its own sentence with "does not fall through," the strictly-sequential guardrail is restated, and a task greps for both.
- **The walk stops at the first roadmap with any unchecked item and idles, ignoring later roadmaps that have eligible work** → Mitigated by D2: "first roadmap *holding an eligible item*" is spelled out and the all-blocked-roadmap case is stated as continuing the walk.
- **A recursive read picks up `docs/roadmaps/archive/` and re-selects completed work forever** → Mitigated by D3: the exclusion is explicit, not implied by the glob.
- **The annotation push force-pushes `main` or clobbers a concurrent edit** → Mitigated by D5: the race procedure is written into the skill (fetch/rebase, re-locate by `**R<n>**`, re-check unchecked and unannotated), force-push is forbidden by name, and the drop-the-annotation outcome is stated for both losing cases.
- **The annotation is written by line number and lands on the wrong item after a concurrent edit** → Mitigated by D5: re-location is specified as being by the `**R<n>**` marker, explicitly not by line number.
- **The annotation rewords or reflows the human's item text** → Mitigated by D4: append-to-end-of-line, existing text byte-identical, same discipline R3 applied to the flip.
- **Having been granted one write, the skill generalizes to flipping boxes or "tidying" a roadmap** → Mitigated by D10: authorship is enumerated and forbidden item by item, and the annotation is explicitly classified as bookkeeping, not authorship.
- **The rewrite quietly keeps a PR-shaped remnant — an `--pr` dispatch, a "for human review" sentence, a stray `gh` command** → Mitigated by a task that greps the finished file for `gh `, `pull request`, `--pr`, `priority:`, `agent:backlog`, `integration branch`, and `arbor-auto-refine` and requires zero hits.
- **A "roadmap complete" observation turns into the skill archiving the file itself** → Mitigated by D6: the skill observes the subagent's already-committed `git mv` and the text says it never moves the file.
- **The quiet idle path acquires a notification because silence feels like a failure** → Mitigated by D7: both suppressions are stated as rules, and a task verifies the notification section enumerates exactly three events.
- **R5's `--goal` mode gets half-built here because the loop is "obvious"** → Mitigated by an explicit non-goal plus a scope requirement and a task: the file must state one cycle per invocation and must not mention `--goal` or a foreground mode at all.
- **Merges now land on `main` without human PR review** → Accepted; it is the roadmap's stated intent. The gate inside `arbor-auto-work` is the quality boundary, and the surviving guardrails (one item per cycle, one subagent, repo-scoped identity, human-authored roadmap as the only source of work) are what bound the blast radius. Operators who need PR review can schedule differently or not enable the skill; that is a deployment decision, not a skill instruction.
- **A blocked item never gets retried by anything** → Accepted and deliberate. R2 dropped refine's blocked-issue triage as an explicit non-goal of the parent roadmap. A human unblocks the item by fixing the cause and deleting the annotation. The skill must not invent a re-attempt policy, and the text should make the human-in-the-loop expectation visible rather than leaving it as an unexplained dead end.

## Migration Plan

Single-file rewrite; no rollout, no data migration, nothing to deploy. Rollback is `git checkout` of `.claude/skills/arbor-auto-developer/SKILL.md`. Downstream repos pick it up the next time `install.sh` refreshes their skill symlinks — skills are symlinked, not copied, so there is nothing to version-pin.

There is one real operational discontinuity for any repo already running the old skill on a schedule: work previously accumulated on an integration branch behind a running PR, and now merges land on `main`. Any open integration-branch PR left over from the old behavior is a human's to review, merge, or close; this change ships no cleanup for it, because the skill no longer knows integration branches exist and adding a one-shot migration path would mean writing the very code the change deletes. Similarly, any open `agent:backlog` issues are left as-is — they are a human's to triage or close, and work that should still happen belongs on a roadmap.

## Open Questions

None blocking. Two items are deliberately deferred: the `--goal` foreground mode (R5, which extends this skill immediately after) and `docs/roadmaps/archive/` existing from the start in freshly scaffolded projects (R6). Neither is needed for this change to be correct on its own — `arbor-auto-work` already creates the archive directory on demand at first use.
