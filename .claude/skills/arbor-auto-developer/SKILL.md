---
name: arbor-auto-developer
description: Reads docs/roadmaps/*.md as the work queue — the human-authored, files-only roadmap set arbor-auto-roadmap produces — excluding docs/roadmaps/archive/. Walks roadmap files in filename order and, within the first roadmap holding an eligible item, selects the earliest incomplete phase's first unchecked, unannotated item. Dispatches exactly one arbor-auto-work subagent, autonomous by default, to build that single item and merge it to main. Never authors roadmap content itself — no item text, no phases, no checkbox flips. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop.
license: MIT
metadata:
  author: arbor
  version: "2.0"
---

# Arbor auto-developer agent

A scheduled burn-down agent. Its queue is `docs/roadmaps/*.md` — the
multi-phase, human-authored roadmaps `arbor-auto-roadmap` writes — never
anything this skill creates, seeds, or files itself. Each run is a single
cycle: read the roadmaps, select the single next eligible item, dispatch one
`arbor-auto-work` subagent to build and merge it, record the outcome, exit.
The `schedule` skill's cron cadence (~hourly; it enforces a 1h minimum
interval) is what provides "keep polling" — this skill never loops
internally, and never runs two subagents at once. Its only real precondition
is that at least one human-authored roadmap file exists under
`docs/roadmaps/`; when none does, that is not a setup failure, it's simply
nothing to do until a human writes one (see step 3, below).

## The cycle

You MUST create a todo per step and complete them in order.

1. **Read the queue.** Read the non-archived roadmap files `docs/roadmaps/*.md`
   as they stand on `main` — not on whatever branch happens to be locally
   checked out, which could be stale relative to a cycle that already merged.
   `docs/roadmaps/archive/` is explicitly excluded: it holds roadmaps a
   previous cycle has already completed and archived, and a recursive search
   (`find`, `rg --files`, `**/*.md`) over `docs/roadmaps/` would resurrect
   that already-done work as an endless supply of "eligible" items. Read only
   the top-level glob.

2. **Select exactly one item.** Walk the non-archived roadmap files in
   filename order. Within the **first roadmap holding an eligible item** —
   not merely the first roadmap with any unchecked item — take that
   roadmap's earliest incomplete phase, and within that phase take the first
   unchecked item that does not carry a blocked annotation
   (`<!-- blocked: ... -->`). That single item is the cycle's selection;
   never select, batch, or queue more than one.

   Phases are the `## Phase <k>: <name>` headings in file order. A phase is
   **incomplete** when at least one item under it is unchecked — whether or
   not that item carries a blocked annotation. A blocked item is still
   unchecked, so it still counts toward its phase being incomplete, and later
   phases in that roadmap stay closed regardless of the annotation.

   Two cases resolve the walk explicitly, because the plausible reading gets
   both of them wrong:

   - **An all-blocked roadmap yields nothing, and the walk moves on.** If
     every unchecked item in a roadmap carries a blocked annotation, that
     roadmap holds no eligible item. Do not end the run here — continue the
     walk to the next roadmap file by filename.
   - **A blocked earliest phase does not fall through to a later phase in the
     same roadmap.** If the earliest incomplete phase's unchecked items are
     all blocked-annotated, do **not** select an item from a later phase of
     that same roadmap, even if that later phase has unchecked, unannotated
     items of its own. Phases are strictly sequential: a later phase is
     never worked while an earlier phase still holds an unchecked item,
     blocked or not. That roadmap yields nothing this cycle, and the walk
     continues to the **next roadmap file** — never to a later phase of this
     one.

3. **If nothing is eligible, end the run quietly.** This covers two distinct
   cases, and both end the run the same way — no dispatch, no notification,
   no error:

   - No eligible item exists in any non-archived roadmap (every roadmap is
     fully checked, or every unchecked item — in the file, or specifically in
     its earliest incomplete phase — carries a blocked annotation).
   - No non-archived roadmap file exists at all under `docs/roadmaps/`, or
     the directory doesn't exist.

   Neither case is a setup failure or a misconfiguration. Do not create
   `docs/roadmaps/`, do not invoke `arbor-auto-roadmap`, and do not report a
   problem — there is simply nothing to do until the next scheduled tick.

4. **Dispatch exactly one subagent** for the selected item (see Subagent
   dispatch, below) and wait for it to finish before doing anything else.

5. **On success** (`outcome: shipped`): confirm the merge actually landed on
   `main` — e.g. `git log main --oneline -1` reflects the returned
   `work_id`/`branch` — rather than taking the subagent's report on faith.
   Send the merge-landed notification (see Notifications).

   Then **observe roadmap completion**; do not compute it independently. If
   the merged item was the last unchecked item in its file, `arbor-auto-work`
   already performed the archival as part of that same work commit: the
   roadmap file is gone from `docs/roadmaps/` and present under
   `docs/roadmaps/archive/`, and the commit body carries a
   `- Roadmap <slug> complete; archived` bullet. When you see that signal,
   treat the roadmap as complete and also send the roadmap-complete
   notification — merge-landed and roadmap-complete are separate events, and
   both fire; neither replaces the other. This skill itself never moves,
   copies, renames, or deletes a roadmap file, and never creates
   `docs/roadmaps/archive/` — that belongs entirely to `arbor-auto-work`'s
   own work commit.

6. **On any outcome other than `shipped`** — a gate failure reported as
   `failed`, or a `blocked` result where the cycle could not run at all:
   dispatch exactly one retry
   subagent, in a fresh context, passing the first attempt's failure output.
   Wait for it to finish before doing anything else — the retry reuses the
   cycle's one subagent slot sequentially; it is never a second, concurrent
   subagent.

   If the retry also fails, stop working this item: never make a third
   attempt on it in this run, and never move on to a different item in its
   place in this run — one run is one cycle, and any other eligible item
   waits for the next scheduled tick.

   **Annotate it as blocked and push the annotation to `main`.** Append
   `<!-- blocked: <reason> -->` to the end of the failed item's line, where
   `<reason>` is a one-line summary of what broke and at which gate step
   (for example: `<!-- blocked: gate failed at tests — 3 failing specs in
   cart module -->`). Leave the item's existing text byte-identical before
   and after — never reword, reflow, re-wrap, or renumber the item or any of
   its continuation lines — and leave its checkbox unchecked. Commit and push
   this single-line change directly to `main`; it must not be left as an
   uncommitted working-tree change or stranded on a side branch. This is
   bookkeeping so a later cycle's walk skips the item and one bad item
   cannot stall the rest of the roadmap — it is not authorship of the item
   (see Guardrails).

   **Handle the push as a race**, because `main` can move between when you
   read the item and when you push the annotation — another cycle's merge, a
   human's commit, a concurrent roadmap edit. If the push is rejected:

   1. Fetch and rebase — or re-pull and re-apply the annotation — onto the
      current `main`.
   2. Re-locate the item's line by its `**R<n>**` marker, never by line
      number: a concurrent edit is the first thing to invalidate a line
      number.
   3. Re-check, on the current `main`, that the item is still `- [ ]` and
      still carries no blocked annotation.
   4. If both still hold, push again. If that push is rejected too, repeat
      from step 1.
   5. If either re-check fails — the item is now `- [x] **R<n>**`, or it
      already carries a blocked annotation — **drop the annotation** instead
      of pushing it. A checked box means the item genuinely got built; an
      existing annotation already achieves the goal. Never force-push `main`
      to make an annotation land — that is never proportionate for a
      bookkeeping comment, no matter how many times the push has been
      rejected.

   Send the blocked notification (see Notifications) once the retry has
   failed for the second time, regardless of whether the annotation push
   landed or was dropped per the rule above — the notification reports that
   the item is blocked, which is true either way.

   Blocked items wait for a human. This skill invents no re-attempt or
   triage policy: nothing here re-attempts a blocked item automatically, on
   this tick or any later one. A human unblocks it by fixing the underlying
   cause and deleting the annotation from the roadmap line; after that, the
   item is eligible again on the next walk.

## Subagent dispatch

Dispatch a fresh subagent with a **self-contained** prompt — it shares no
context with this cycle, so hand it everything it needs rather than a
pointer back to the roadmap:

- The selected item's **full text**, verbatim — the why-plus-acceptance-
  criteria `arbor-auto-roadmap` requires each item to be phrased as.
- The item's reference in the form `roadmap:docs/roadmaps/<slug>.md#R<n>`,
  exactly as `arbor-auto-work` documents it, so it can validate the item and
  flip its checkbox on a successful commit.
- An instruction to run the `arbor-auto-work` skill in **autonomous mode —
  its default: no `--interaction`, no `--pr`.**

Do not instruct the subagent to override the merge target. `main` is already
`arbor-auto-work`'s own default, so nothing here directs it to branch off,
or merge into, anything else.

The subagent returns a compact result: `{ outcome, work_id, branch, note }`.
Read `outcome` to drive the success/retry/blocked branching in steps 5 and 6
above, and quote `work_id` and `branch` in notifications. Treat it as a
two-way branch, so that every possible value is handled: `shipped` means the
merge landed and routes to step 5; **anything else** means it did not, and
routes to step 6 — `failed` for a gate failure, `blocked` where the cycle
could not run at all (`arbor-auto-work` stops before committing if, say, the
`roadmap:` reference does not resolve), and likewise a missing or
unrecognised value. Step 6's retry-then-annotate path is the correct response
in every one of those cases: the retry either clears a transient problem or
confirms the item genuinely cannot be built right now, and the annotation
then stops that one item from stalling the roadmap.

Exactly one subagent is in flight at any moment — never two. The cycle waits
for the dispatched subagent to finish before doing anything else, including
before dispatching a retry; a retry subagent is only ever dispatched after
the first attempt has completed.

## Notifications

Send a `PushNotification` — one line, under 200 characters, leading with
what's actionable — on exactly these three events, and no others:

- **Merge landed** — the dispatched subagent's merge landed on `main`.
- **Item blocked after retry** — the retry also failed and the item's
  two-attempt budget is exhausted for this run.
- **Roadmap complete** — the item just merged was the last unchecked item in
  its file.

Merge-landed and roadmap-complete can both be true of the same cycle; when
they are, send both — neither replaces the other.

**Do not notify on dispatch**, and **do not notify on a quiet idle run** —
these are rules, not omissions. A subagent starting work is not yet an
outcome, and an hourly cron reporting "nothing to do" on every tick trains
the operator to ignore the channel, which then also buries the notifications
that actually matter.

If `PushNotification` is unavailable in this run's environment, continue
without failing the run — the merge on `main`, the blocked annotation, and
the archived roadmap file are all durable records regardless of whether the
notification itself was delivered.

## Guardrails

- **Phases are strictly sequential.** A later phase is never worked while an
  earlier phase in the same roadmap still holds an unchecked item —
  blocked-annotated or not. A fully blocked earliest phase does not open the
  door to a later phase; it closes that roadmap for the cycle instead.
- **Exactly one subagent in flight at a time, never two.** A retry follows
  the first attempt sequentially, once it has finished; it never overlaps
  it.
- **At most two attempts per item per run** — one original plus one retry —
  on the same roadmap item. A third attempt, in this run, is never made, and
  a different item is never picked up in its place within the same run.
- **One run = one cycle.** Do not loop internally; exit as soon as the item
  is handled (merged, or blocked-and-annotated) or the walk finds nothing
  eligible, and let the scheduler bring you back.
- **Repo-scoped, maintainer identity only.** Only ever touch branches and
  roadmap files in this repo, under the maintainer's own identity — no
  cross-repo activity.
- **Never author roadmap content.** Never write or edit an item's text,
  never add, remove, or rename a phase, never flip a checkbox in either
  direction, and never invoke `arbor-auto-roadmap`. The checkbox flip
  belongs entirely to `arbor-auto-work`, inside its own work commit — this
  skill does not flip one itself even when it observes a merge that plainly
  should have flipped one; an unflipped box after a merge is an upstream bug
  in the work cycle, not something to patch here.
- **The blocked annotation is the one exception, and it is bookkeeping, not
  authorship.** Appending `<!-- blocked: <reason> -->` to a twice-failed
  item's line is the single write this skill ever makes to a roadmap file.
  It records what happened to an item; it does not write what the item is.
  Being granted this one write licenses nothing else on the list above.
