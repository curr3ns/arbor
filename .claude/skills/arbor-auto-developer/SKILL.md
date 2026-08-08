---
name: arbor-auto-developer
description: Reads docs/roadmaps/*.md as the work queue — the human-authored, files-only roadmap set arbor-auto-roadmap produces — excluding docs/roadmaps/archive/. Walks roadmap files in filename order and, within the first roadmap holding an eligible item, selects the earliest incomplete phase's first unchecked, unannotated item. Dispatches exactly one arbor-auto-work subagent, autonomous by default, to build that single item and merge it to main. Never authors roadmap content itself — no item text, no phases, no checkbox flips. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop. Also supports an optional foreground --goal mode — invoked with --goal, it sets a session-scoped /goal Stop hook naming one target roadmap and works that roadmap's items one at a time, cycle after cycle, until the roadmap is complete and archived or nothing eligible remains in it — falling back to running cycles back-to-back in-session when /goal is unavailable. The scheduled default with no --goal is unaffected.
license: MIT
metadata:
  author: arbor
  version: "2.1"
---

# Arbor auto-developer agent

A scheduled burn-down agent. Its queue is `docs/roadmaps/*.md` — the
multi-phase, human-authored roadmaps `arbor-auto-roadmap` writes — never
anything this skill creates, seeds, or files itself. Each run is a single
cycle: read the roadmaps, select the single next eligible item, dispatch one
`arbor-auto-work` subagent to build and merge it, record the outcome, exit.
The `schedule` skill's cron cadence (~hourly; it enforces a 1h minimum
interval) is what provides "keep polling" for that default path — this
skill never loops internally there, and never runs two subagents at once,
in either mode. The one documented exception to "never loops internally" is
the foreground `--goal` mode below, where the skill's own cycle repeats,
across a whole run, instead of waiting for the next scheduled tick. Its
only real precondition is that at least one human-authored roadmap file
exists under `docs/roadmaps/`; when none does, that is not a setup failure,
it's simply nothing to do until a human writes one (see step 3, below).

**Two modes.** Everything above describes the **default, scheduled mode** —
no flag — which is unattended, paced entirely by that cron tick, and always
exactly one cycle per invocation. The **foreground goal mode** — `--goal` —
is different on both axes: it is human-invoked, and it runs not to the next
tick but to a stated finish line, working a single named roadmap one item
at a time until that roadmap is complete or nothing eligible remains in it
(see `## Foreground goal mode (--goal)`, below). Without `--goal`, none of
that applies — the skill runs exactly one cycle per invocation, exactly as
described above; `--goal` is the only thing that changes it.

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
   waits for the next scheduled tick. Under `--goal`, the first two rules
   are unchanged: still no third attempt on this item anywhere in the run,
   and this cycle still ends here rather than chaining into a replacement.
   Only the last clause differs — there is no scheduled tick to wait for,
   so the next eligible item is picked up by the goal run's **next cycle**
   instead, whose step-1 walk already sees this item's annotation (see
   `## Foreground goal mode (--goal)`, and the two `--goal` guardrails
   below).

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

## Foreground goal mode (--goal)

Invoked as `arbor-auto-developer --goal [<roadmap>]`, this mode works a
single roadmap to completion in one sitting, one item at a time, by
wrapping the same cycle `## The cycle` already specifies inside `/goal`'s
session-scoped Stop hook. Everything below is additional to `## The
cycle`, `## Subagent dispatch`, and `## Notifications` — a goal run's
individual cycles behave exactly as those sections already describe. This
section governs only what happens *around* the cycle: what condition gets
set, which roadmap is targeted, how the run keeps going between cycles,
how it terminates, and what happens when `/goal` itself is unavailable.

### Setting the goal

Before doing anything else, set a goal via `/goal <condition>` with the
condition:

> Every item in `docs/roadmaps/<slug>.md` is checked off and the file has been migrated to `docs/roadmaps/archive/`

with `<slug>` replaced by the target roadmap's actual slug (see Target
roadmap, below) — never left as the literal text `<slug>`. `/goal` installs
a **session-scoped Stop hook**: it is the hook, not this skill, that keeps
the session going between items, re-evaluating the condition each time the
session tries to stop, and it is the hook that auto-clears itself the
moment the condition holds.

The condition names exactly one roadmap and always keeps the archival
clause. `arbor-auto-work` `git mv`s a completed roadmap out of
`docs/roadmaps/` into `docs/roadmaps/archive/` as part of the commit that
closes its last item, so a condition phrased only against the original
`docs/roadmaps/<slug>.md` path would, at the very moment of success, be
evaluated against a file that no longer exists there. Naming the migration
is what turns the file's disappearance into the success signal instead of
an ambiguity.

Set the goal exactly once, at the start of the run, and never re-issue
`/goal` with a different condition mid-session — the roadmap the condition
names does not change for the life of the run (see Completion handoff,
below, for what happens once the target finishes).

### Target roadmap

`--goal` takes an optional roadmap argument — a slug (for example
`roadmap-native-workcycles`) or a full `docs/roadmaps/<slug>.md` path. When
one is given, that roadmap is the target. When the named roadmap is not
present among the non-archived `docs/roadmaps/*.md` files, stop the run and
report that it was not found — never select a different roadmap in its
place.

With no argument, the target is the **first roadmap holding an eligible
item**, found by the skill's existing filename-order walk (`## The cycle`,
step 2) — the same selection the default mode already makes. This
introduces no new ordering key and no new selection rule.

However it is found, the target is resolved **once**, at the start of the
run, and then **pinned** for the rest of the run rather than re-derived on
every iteration. Pinning matters because the walk runs against a moving
`main`: if the target were re-derived each time, a blocked annotation
landing in an earlier roadmap, or a human's concurrent edit, could shift
the walk onto a different file while the `/goal` condition still names the
original — the skill would then be working roadmap B toward a condition
that only roadmap A's completion can satisfy, which can then never clear.
When the session resumes after a Stop-hook re-prompt, recover the target
from `/goal active` rather than re-running the walk; `/goal active` is the
authoritative record of what this run committed to, and it survives across
a re-prompt the way in-context state does not.

Two degenerate starts both resolve the same way: **no goal is set**, the
skill reports why, and it exits on the same quiet path a scheduled idle
run takes (`## The cycle`, step 3).

- No non-archived roadmap holds an eligible item at all.
- The named roadmap exists but holds no eligible item (every item blocked,
  or every item checked but the file not yet archived).

### Working items one at a time

The goal run works items **one at a time** — the same single dispatch per
cycle the default mode performs (`## The cycle`, steps 2 and 4), repeated
for as long as the run continues. Nothing about goal mode changes what a
cycle does; it changes how many cycles happen and what brings the next one
about.

Exactly **one subagent is in flight at any moment across the entire goal
run**, retries included — never two, and never a batch. A retry is
dispatched only after the attempt it is retrying has finished, exactly as
in the default mode; goal mode does not relax this for the sake of
finishing sooner. Each cycle completes fully — dispatch, verification, and
the resulting notification or blocked annotation — before the next cycle
begins, and each new cycle re-reads the roadmap queue from `main` (step 1),
so the previous cycle's merge or annotation is already visible to the walk
that selects the next item.

Under `/goal`, the repetition belongs to the **hook**, not to this skill's
own control flow: the skill runs one cycle per turn and then tries to
stop; the Stop hook is what intercepts that and brings the session back
for another turn, re-evaluating the condition each time. The skill does
**not** additionally loop internally while a live Stop hook is driving the
session — setting the goal and also looping in-session would double the
work per turn and put a second subagent in flight, which is exactly the
failure this file rules out. (The fallback, below, is the one case where
the skill does loop in-session, because there is no hook to do it
instead.)

"Foreground" describes the human watching the session, not approval
prompts. Dispatch stays autonomous: subagents still run `arbor-auto-work`
in its default mode, with no `--interaction` and no `--pr`, exactly as
`## Subagent dispatch` specifies for the default path.

### Termination: why the loop cannot livelock

Both the `/goal` path and the fallback (below) terminate on the same
condition: **no eligible item remains in the target roadmap** — either
because the roadmap is finished and has been archived, or because every
unchecked item left in it carries a `<!-- blocked: ... -->` annotation. An
all-blocked roadmap is a **terminating state, not a retry state**: the
goal run does not re-attempt blocked items to keep itself going, and it
does not invent a triage pass over them — `## The cycle` step 6's rule
that blocked items wait for a human holds here unchanged.

The loop cannot livelock, and here is the argument for why. Every
iteration ends in exactly one of two ways: either the dispatched item
**merges**, and the roadmap has one fewer unchecked item; or the item
exhausts its two attempts, gets annotated blocked, and the roadmap has one
fewer *eligible* item — the annotation, once pushed to `main`, is what
makes the next iteration's walk skip it. Both quantities are non-negative
integers over a finite item set, and both strictly decrease on every
iteration that produces them. There is no third outcome that leaves both
unchanged. The loop therefore reaches "no eligible item" in a bounded
number of iterations — at most as many as the roadmap has unchecked items
— and terminates.

As belt and braces, the goal run also keeps a **session-local record of
items it has exhausted during the run** and treats them as ineligible for
the remainder of the run, regardless of whether the blocked-annotation
push landed on `main`. This matters because step 6's push-as-a-race
procedure legitimately *drops* the annotation in two cases — the item was
independently checked off, or another actor already annotated it — and
while both of those outcomes happen to leave the item ineligible on the
next walk anyway, a termination argument that depends on a push having
succeeded is weaker than one that does not.

### Clearing the goal on an unsatisfied terminal state

When the loop terminates without the condition holding — the all-blocked
case, or any other case where the run ends with the target roadmap neither
finished nor archived — issue `/goal clear` **itself**, before stopping.
The reason: in that state the condition is false and will stay false,
since nothing further is going to happen to this roadmap without a human;
a Stop hook left active would keep re-prompting a session that has
correctly concluded there is nothing left to do, forever. Report which
items are blocked and why as part of stopping, so a human can act without
re-reading the roadmap.

When the condition **does** hold — the target roadmap is finished and
archived — rely on the hook's own auto-clear instead; do not issue `/goal
clear` in that case, and do not treat it as required. The two terminal
states are asymmetric on purpose: one needs the skill to intervene, the
other does not.

### `/goal` availability and the fallback

`/goal` requires a **trusted workspace** and **unrestricted hooks**. It
fails in an untrusted workspace ("/goal is only available in trusted
workspaces. Restart, accept the trust dialog, and try again.") and it
fails when hooks are restricted — either `disableAllHooks` or
`allowManagedHooksOnly` set in settings or by policy ("/goal can't run
while hooks are restricted (disableAllHooks or allowManagedHooksOnly is
set in settings or by policy)."). Stop hooks are also **REPL-only**, so a
non-REPL invocation of this skill cannot have one either — a third,
independent reason `/goal` may be unavailable, on top of the two settings
above.

When `/goal` cannot be set for any of these reasons, do not abort the run.
Instead, **report which reason applied** — untrusted workspace,
`disableAllHooks`, `allowManagedHooksOnly`, or non-REPL — as prose in the
session (this report is not a `PushNotification`; the notification set
stays exactly the three events in `## Notifications`), and then **fall
back to running cycles back-to-back in-session**: the same single-item
cycle described in `## The cycle` and in Working items one at a time,
above, dispatched one after another, each one waited out before the next
begins, until no eligible item remains in the target roadmap. The fallback
is not a second algorithm — it shares the target-selection rule, the
one-subagent guardrail, the attempt budget, and the termination condition
with the `/goal` path; the only thing missing is the hook, so the skill
supplies the repetition itself instead of relying on one.

### Completion handoff

A goal run finishes **one** roadmap. If the target completes — the
condition holds and the hook clears — while other non-archived roadmaps
still hold eligible items, the run ends there; it does not roll onto
another roadmap in the same run. (The condition names one `<slug>`, and
re-issuing `/goal` with a different condition mid-session is exactly what
Setting the goal, above, rules out.) The closing report names which
roadmaps still hold eligible work and states the invocation that would
continue with the next one — `--goal` with no argument, or `--goal
<next-slug>` — so a human who wants to keep going knows the one command to
type.

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
- **Under `--goal`, that budget is per item, not per run.** A goal run spans
  many items across many cycles, so "per run" here reads as **per item**: at
  most two attempts — one original plus one retry — on the same item,
  however many other items the run has already worked. An item that
  exhausts its budget is annotated blocked and is thereafter skipped by the
  walk, so it never gets a third attempt later in the same goal run either.
  This does not loosen the guardrail above; it says what "run" scopes to
  once a run can span more than one item.
- **Under `--goal`, "never move on to a different item in its place" is a
  within-cycle rule.** A cycle that exhausts its budget does not chain into
  a different item — it ends, annotated blocked. A goal run reaches its
  next item only by **starting a new cycle**, whose step-1 walk re-reads
  `main` and so already sees the annotation; that is a new cycle selecting
  a new item, not a failed cycle picking a replacement, and it is how
  `## Foreground goal mode (--goal)` continues past a blocked item without
  contradicting this guardrail.
- **One run = one cycle — on the default, scheduled invocation.** Do not
  loop internally; exit as soon as the item is handled (merged, or
  blocked-and-annotated) or the walk finds nothing eligible, and let the
  scheduler bring you back. The one exception is `--goal`
  (`## Foreground goal mode (--goal)`): when that flag was passed, this
  repetition is licensed — by the Stop hook on the `/goal` path, or
  in-session on the fallback — until the goal run's own termination
  condition (same section) is met.
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
