---
name: arbor-auto-developer
description: Burns down a repo's work queue, one item per run. Prefers the repo's issue tracker when it has one — GitHub issues (gh authenticated, issues enabled), or the Jira project .arbor/config.json records when its roadmap destination is jira — and at least one eligible open issue, selecting the highest-priority unclaimed issue and dispatching one arbor-auto-work cycle in issue mode (issue:<n> or jira:<KEY-n>). Otherwise falls back to docs/roadmaps/*.md, the human-authored, files-only roadmap set arbor-auto-roadmap produces (excluding docs/roadmaps/archive/), walking roadmap files in filename order and, within the first roadmap holding an eligible item, selecting the earliest incomplete phase's first unchecked, unannotated item. One queue per cycle, exactly one arbor-auto-work subagent, autonomous by default, merged to main. Never authors queue content itself — no issues filed or re-scoped, no item text, no phases, no checkbox flips. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop. Also supports an optional foreground --goal mode — invoked with --goal, it sets a session-scoped /goal Stop hook naming one target queue (the issue tracker, optionally scoped to a label, or one named roadmap) and works that queue one item at a time, cycle after cycle, until nothing eligible remains in it — falling back to running cycles back-to-back in-session when /goal is unavailable. The scheduled default with no --goal is unaffected.
license: MIT
metadata:
  author: arbor
  version: "2.3"
---

# Arbor auto-developer agent

A scheduled burn-down agent. It has two possible queues and each cycle uses
exactly one of them. Where the repo has an issue tracker available — GitHub
issues, or Jira when the repo records Jira as its roadmap destination — the
queue is **the issue tracker**; where it does not, the queue is `docs/roadmaps/*.md` —
the multi-phase, human-authored roadmaps `arbor-auto-roadmap` writes. Either
way the content of that queue is the developer's, never anything this skill
creates, seeds, or files itself. Each run is a single cycle: detect the queue,
select the single next eligible item, dispatch one `arbor-auto-work` subagent
to build and merge it, record the outcome, exit.
The `schedule` skill's cron cadence (~hourly; it enforces a 1h minimum
interval) is what provides "keep polling" for that default path — this
skill never loops internally there, and never runs two subagents at once,
in either mode. The one documented exception to "never loops internally" is
the foreground `--goal` mode below, where the skill's own cycle repeats,
across a whole run, instead of waiting for the next scheduled tick. Its
only real precondition is that one of the two queues holds something to
build — an eligible open issue, or a human-authored roadmap file under
`docs/roadmaps/`. When neither does, that is not a setup failure, it's
simply nothing to do until a human files an issue or writes a roadmap
(see step 3, below).

**Two modes.** Everything above describes the **default, scheduled mode** —
no flag — which is unattended, paced entirely by that cron tick, and always
exactly one cycle per invocation. The **foreground goal mode** — `--goal` —
is different on both axes: it is human-invoked, and it runs not to the next
tick but to a stated finish line, working a single pinned queue one item at a
time until nothing eligible remains in it (see `## Foreground goal mode
(--goal)`, below). Without `--goal`, none of
that applies — the skill runs exactly one cycle per invocation, exactly as
described above; `--goal` is the only thing that changes it.

## The cycle

You MUST create a todo per step and complete them in order.

1. **Detect the queue.** Two queues exist; this cycle uses exactly one of
   them, and the issue tracker wins whenever it is available.

   **Which tracker?** Read `.arbor/config.json` as it stands on `main`. If
   `roadmap.destination` is `jira`, the tracker is the Jira project named by
   `roadmap.jira.project`, and every tracker operation in this file — the
   lock check, the eligibility probe, the close-out check, the blocked record
   — runs through its Jira equivalent (see **Jira as the tracker**, below).
   Otherwise — no file, no `roadmap` key, or any other destination — the
   tracker is GitHub, as described next. The config picks exactly one
   tracker; a Jira repo is never also probed for GitHub issues.

   **Is the issue tracker available?** For GitHub, it is when `gh` is
   installed and authenticated and the repo has issues enabled:

   ```bash
   gh auth status
   gh repo view --json hasIssuesEnabled -q .hasIssuesEnabled
   ```

   Either command failing — no `gh` on `PATH`, not authenticated, no GitHub
   remote, issues disabled on the repo — means the tracker is not available.
   For Jira, it is available when `arbor-auto-work`'s Jira access check
   passes (its `## Jira mode`); a failure there means the same thing.
   That is not an error and not something to fix: fall through to the roadmap
   queue below, exactly as a repo that never had issues would.

   **Is another cycle already working?** Where the tracker is available, check
   the lock `arbor-auto-work` claims an issue with, before selecting anything:

   ```bash
   gh issue list --label "agent:working" --state open
   ```

   If that returns an issue, a cycle already owns it. End the run on the quiet
   path (step 3): no dispatch, no notification, and no attempt to steal or
   clear the lock — a live cycle's claim is not this skill's to revoke, and
   two cycles at once is exactly what the lock exists to prevent. The one
   exception is the stale lock this skill's own cycle left behind on an issue
   it then blocked; step 6 covers that, and only that.

   Say which issue holds the lock as prose in the session, so a stalled loop
   is visible in the run's own output. This is not a fourth notification
   event (`## Notifications`) — a held lock normally means a cycle is doing
   its job. A lock held while no cycle is running is stale, and clearing it
   is the developer's call, made by removing `agent:working` from that issue;
   this skill never makes it for them.

   **Which queue, then?** Probe the tracker for an eligible issue:

   ```bash
   gh issue list --state open --limit 50 \
     --json number,title,labels,assignees,createdAt,body
   ```

   An issue is **eligible** when it is open, is not a pull request, is
   unassigned, and carries none of `agent:blocked`,
   `agent:needs-clarification`, or `epic` — the same eligibility
   `arbor-auto-work`'s `issue:next` applies.

   `epic` marks a developer-authored umbrella or tracking issue: it exists as
   a scope reference for the issues carved out of it, and is never implemented
   directly. Unlike the `agent:*` labels it is permanent and belongs to the
   developer — a cycle never adds it, never clears it, and never treats it as
   a block to escalate. It is simply not work, so selection passes over it in
   silence rather than reporting anything.

   In Jira, `epic` is the Epic issue type rather than a label, and the
   `agent:*` labels are spelled `agent-*`; the eligibility query in
   `arbor-auto-work`'s `## Jira mode` encodes all of it.

   If at least one issue is eligible, this cycle runs on the **issue queue**,
   and the roadmap walk below is skipped entirely. If the tracker is
   unavailable, or no issue is eligible, this cycle runs on the **roadmap
   queue**.

   **The roadmap queue.** Read the non-archived roadmap files
   `docs/roadmaps/*.md` as they stand on `main` — not on whatever branch
   happens to be locally checked out, which could be stale relative to a cycle
   that already merged. `docs/roadmaps/archive/` is explicitly excluded: it
   holds roadmaps a previous cycle has already completed and archived, and a
   recursive search (`find`, `rg --files`, `**/*.md`) over `docs/roadmaps/`
   would resurrect that already-done work as an endless supply of "eligible"
   items. Read only the top-level glob.

   **One queue per cycle, never both.** A cycle that selected an issue does
   not also flip a roadmap item, and a cycle that selected a roadmap item does
   not also claim an issue.

   **Jira as the tracker.** `arbor-auto-work`'s `## Jira mode` is the single
   definition of every Jira operation — its lock query, eligibility query and
   ordering, claim, label swap, comment, unassign, and close. This skill uses
   those as written rather than keeping a second copy. Wherever this file
   shows a `gh` command, a Jira-tracker cycle runs that operation's Jira
   equivalent instead; wherever it names an `agent:*` label, read the
   `agent-*` spelling; wherever it names an issue `#<n>`, read the issue key
   `<KEY-n>`. Nothing else about the cycle changes.

2. **Select exactly one item** from the queue step 1 chose. That single item
   is the cycle's selection; never select, batch, or queue more than one, on
   either queue.

   **On the issue queue**, take the first eligible issue in
   `arbor-auto-work`'s own order: priority label `p0` > `p1` > `p2` >
   unlabelled, then oldest `createdAt` — or, in Jira, Priority highest first,
   then oldest `created`. That skill's issue-mode resolution of
   `issue:next` is the single definition of this ordering; follow it rather
   than maintaining a second copy, and treat it as the authority if the two
   ever read differently. Hold the issue's number, title, and body for the
   dispatch.

   Resolve the number here rather than leaving selection to the subagent's
   `issue:next`: this cycle needs the number for its own notifications and for
   the blocked bookkeeping in step 6, and the subagent's compact result does
   not carry it back.

   **On the roadmap queue**, walk the non-archived roadmap files in
   filename order. Within the **first roadmap holding an eligible item** —
   not merely the first roadmap with any unchecked item — take that
   roadmap's earliest incomplete phase, and within that phase take the first
   unchecked item that does not carry a blocked annotation
   (`<!-- blocked: ... -->`).

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

3. **If nothing is eligible, end the run quietly.** This covers several
   distinct cases, and every one of them ends the run the same way — no
   dispatch, no notification, no error:

   - Another cycle holds the `agent:working` lock (step 1).
   - The issue tracker is available but no open issue is eligible (every one
     is closed, assigned, or labelled `agent:blocked`,
     `agent:needs-clarification`, or `epic`) **and** the roadmap queue then
     yields nothing either.
   - No eligible item exists in any non-archived roadmap (every roadmap is
     fully checked, or every unchecked item — in the file, or specifically in
     its earliest incomplete phase — carries a blocked annotation).
   - No non-archived roadmap file exists at all under `docs/roadmaps/`, or
     the directory doesn't exist.

   None of these is a setup failure or a misconfiguration. Do not create
   `docs/roadmaps/`, do not invoke `arbor-auto-roadmap`, never open an issue
   to give yourself something to do, and do not report a problem — there is
   simply nothing to do until the next scheduled tick.

4. **Dispatch exactly one subagent** for the selected item (see Subagent
   dispatch, below) and wait for it to finish before doing anything else.

5. **On success** (`outcome: shipped`): confirm the merge actually landed on
   `main` — e.g. `git log main --oneline -1` reflects the returned
   `work_id`/`branch` — rather than taking the subagent's report on faith.
   Send the merge-landed notification (see Notifications).

   **On the issue queue**, the close-out is observed, not performed.
   `arbor-auto-work` closes the issue — through `Closes #<n>`, or explicitly
   where that did not take — swaps `agent:working` for `agent:done`, and posts
   the closing comment, all as part of its own step 10. Confirm it happened:

   ```bash
   gh issue view <n> --json state,labels
   ```

   In Jira, confirm the issue's status category is Done and it carries
   `agent-done` rather than `agent-working`.

   An issue still open, or still labelled `agent:working`, after a merge that
   demonstrably landed is an upstream bug in the work cycle: report it in the
   session and leave the issue alone. Do not close it, swap its label, or post
   its closing comment yourself — the same reason this skill never flips a
   roadmap checkbox it merely observed should have been flipped.

   There is no issue-queue analogue of the roadmap-complete event. An emptied
   tracker is not a milestone; it is simply a quiet tick (step 3) next time.

   **On the roadmap queue**, **observe roadmap completion**; do not compute
   it independently. If the merged item was the last unchecked item in its
   file, `arbor-auto-work` already performed the archival as part of that
   same work commit: the
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
   instead, whose step-1 read of the pinned queue already sees this item's
   blocked record — the annotation, or the label (see
   `## Foreground goal mode (--goal)`, and the two `--goal` guardrails
   below).

   **Record the block on the queue the item came from.** This is the one
   write this skill ever makes to a queue, and it is bookkeeping — so a later
   walk skips the item and one bad item cannot stall the rest of the queue —
   never authorship of what the item is (see Guardrails).

   **On the issue queue**, that record is a label and a comment:

   ```bash
   gh issue edit <n> --add-label "agent:blocked" \
     --remove-label "agent:working" --remove-assignee @me
   gh issue comment <n> --body "<what broke, and at which gate step>"
   ```

   In Jira: add `agent-blocked`, remove `agent-working`, unassign, and
   comment, using `## Jira mode`'s commands.

   Read the issue's current labels first. `arbor-auto-work`'s own escalation
   path writes exactly this record when it escalates, and it may have written
   `agent:needs-clarification` instead, where the intent rather than the gate
   was the problem. If either label is already present, the record exists —
   leave it as it stands and do not post a second comment. What is yours to
   clear is only the residue of a subagent that died without escalating: a
   stale `agent:working` on **this cycle's own issue**, removed alongside the
   `agent:blocked` you add. Never touch the lock on any other issue.

   Never edit the issue's title or body, and never close it. A blocked issue
   stays open because it is waiting for a human; closing it would hide the
   work rather than park it.

   **On the roadmap queue**, that record is an annotation pushed to `main`.
   Append `<!-- blocked: <reason> -->` to the end of the failed item's line,
   where `<reason>` is a one-line summary of what broke and at which gate
   step (for example: `<!-- blocked: gate failed at tests — 3 failing specs
   in cart module -->`). Leave the item's existing text byte-identical before
   and after — never reword, reflow, re-wrap, or renumber the item or any of
   its continuation lines — and leave its checkbox unchecked. Commit and push
   this single-line change directly to `main`; it must not be left as an
   uncommitted working-tree change or stranded on a side branch.

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

   The race is the roadmap queue's alone: a label edit is applied server-side
   against the issue's current state, so there is no local copy to rebase and
   nothing to re-locate.

   Send the blocked notification (see Notifications) once the retry has
   failed for the second time — regardless of whether the annotation push
   landed or was dropped per the rule above, and regardless of whether the
   issue's `agent:blocked` label was already in place when you got there. The
   notification reports that the item is blocked, which is true either way.

   Blocked items wait for a human. This skill invents no re-attempt or
   triage policy: nothing here re-attempts a blocked item automatically, on
   this tick or any later one. A human unblocks it by fixing the underlying
   cause and then clearing the record — deleting the annotation from the
   roadmap line, or removing the `agent:blocked` label from the issue. After
   that, the item is eligible again on the next detection and walk.

## Foreground goal mode (--goal)

Invoked as `arbor-auto-developer --goal [<target>]`, this mode works a
single queue to exhaustion in one sitting, one item at a time, by wrapping
the same cycle `## The cycle` already specifies inside `/goal`'s
session-scoped Stop hook. The queue is the issue tracker or one named
roadmap; which one is decided once, at the start of the run (see Target
queue, below). Everything below is additional to `## The cycle`,
`## Subagent dispatch`, and `## Notifications` — a goal run's individual
cycles behave exactly as those sections already describe. This section
governs only what happens *around* the cycle: what condition gets set,
which queue is targeted, how the run keeps going between cycles, how it
terminates, and what happens when `/goal` itself is unavailable.

### Setting the goal

Before doing anything else, resolve the target queue (see Target queue,
below) and set a goal via `/goal <condition>` with the condition that
matches it.

**Issue queue**, unscoped:

> No open issue in this repository is eligible — every open issue is closed, assigned, or labelled `agent:blocked`, `agent:needs-clarification`, or `epic`

**Issue queue**, scoped to a label:

> No open issue labelled `<x>` in this repository is eligible — every such issue is closed, assigned, or labelled `agent:blocked`, `agent:needs-clarification`, or `epic`

with `<x>` replaced by the actual label. On a Jira tracker, write the
conditions with Jira's terms — "every open issue in Jira project `<KEY>` that
is not an Epic is done, assigned, or labelled `agent-blocked` or
`agent-needs-clarification`" — with `<KEY>` replaced by the actual project.

**Roadmap queue:**

> Every item in `docs/roadmaps/<slug>.md` is checked off and the file has been migrated to `docs/roadmaps/archive/`

with `<slug>` replaced by the target roadmap's actual slug — never left as
the literal text `<slug>`, and likewise never the literal `<x>` above.

`/goal` installs a **session-scoped Stop hook**: it is the hook, not this
skill, that keeps the session going between items, re-evaluating the
condition each time the session tries to stop, and it is the hook that
auto-clears itself the moment the condition holds.

The roadmap condition names exactly one roadmap and always keeps the
archival clause. `arbor-auto-work` `git mv`s a completed roadmap out of
`docs/roadmaps/` into `docs/roadmaps/archive/` as part of the commit that
closes its last item, so a condition phrased only against the original
`docs/roadmaps/<slug>.md` path would, at the very moment of success, be
evaluated against a file that no longer exists there. Naming the migration
is what turns the file's disappearance into the success signal instead of
an ambiguity.

The issue condition names no individual issue — the queue itself is the
target — and it is phrased against **eligibility**, never emptiness. An
issue this run blocks stays open by design (step 6), so a condition like
"every issue is closed" could not clear even on a run that did everything
correctly, and the hook would re-prompt a finished session forever.

Set the goal exactly once, at the start of the run, and never re-issue
`/goal` with a different condition mid-session — the queue the condition
names does not change for the life of the run (see Completion handoff,
below, for what happens once the target finishes).

### Target queue

`--goal` takes an optional argument, and what that argument names decides
the queue:

- **A roadmap** — a slug (for example `roadmap-native-workcycles`) or a full
  `docs/roadmaps/<slug>.md` path matching a non-archived roadmap file. That
  roadmap is the target, on the roadmap queue, whether or not the issue
  tracker is available.
- **A label** — any other argument matching an existing label on the
  tracker: a GitHub label on this repo (for example `p0`), or, on a Jira
  tracker, a label carried by at least one issue in the project (for example
  `roadmap-checkout`, which `arbor-auto-roadmap` puts on every item it
  files). The target is the issue queue, scoped to issues
  carrying that label; every eligibility rule from `## The cycle` step 1
  still applies on top of the scope.
- **Neither** — an argument matching no non-archived roadmap and no existing
  label. Stop the run and report it. Never fall back to a different target,
  and never create the label or the roadmap to make the argument valid.

With no argument, the target is whichever queue step 1's detection selects:
the **issue queue, unscoped**, when the tracker is available and holds an
eligible issue; otherwise the **first roadmap holding an eligible item**,
found by the skill's existing filename-order walk (`## The cycle`, step 2) —
the same selection the default mode already makes. This introduces no new
ordering key and no new selection rule.

However it is found, the target — the queue kind, plus the roadmap slug or
label scope narrowing it — is resolved **once**, at the start of the run,
and then **pinned** for the rest of the run rather than re-derived on
every iteration. Pinning matters because detection and the walk both run
against a moving `main` and a moving tracker: if the target were re-derived
each time, a blocked annotation landing in an earlier roadmap, a human's
concurrent edit, or the last eligible issue being claimed could shift the
target onto a different file or a different queue while the `/goal`
condition still names the original — the skill would then be working
roadmap B, or the roadmap queue at all, toward a condition that only
roadmap A's completion, or the tracker's exhaustion, can satisfy, which can
then never clear. A run pinned to the issue queue likewise does not drift
onto a roadmap because the tracker went briefly unreachable.

When the session resumes after a Stop-hook re-prompt, recover the target
from `/goal active` rather than re-running detection; `/goal active` is the
authoritative record of what this run committed to, and it survives across
a re-prompt the way in-context state does not.

Three degenerate starts all resolve the same way: **no goal is set**, the
skill reports why, and it exits on the same quiet path a scheduled idle
run takes (`## The cycle`, step 3).

- Neither queue holds an eligible item at all.
- The named roadmap exists but holds no eligible item (every item blocked,
  or every item checked but the file not yet archived).
- The named label exists but no issue carrying it is eligible.

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
the resulting notification or blocked record — before the next cycle
begins, and each new cycle re-reads the pinned queue (step 1), so the
previous cycle's merge, annotation, or label is already visible to the
selection that picks the next item.

Each cycle's step 1 runs **within the pinned queue**, not across both.
Detection's "the issue tracker wins whenever it is available" decides the
queue once, at the start of a goal run; it does not re-decide per cycle. A
run pinned to a roadmap keeps working that roadmap even if an eligible
issue appears mid-run, and a run pinned to the issue queue does not fall
through to a roadmap when the tracker empties — the tracker emptying is the
run's terminating condition, not a reason to switch queues. The lock check
still runs every cycle on the issue queue, and a lock held by another cycle
ends the run on the quiet path exactly as it would a scheduled cycle.

Where the pin carries a label scope, every cycle's selection is restricted
to issues carrying that label — `gh issue list --state open --label "<x>"`,
or `AND labels = "<x>"` added to the Jira eligibility query — and the ordering
within that subset is unchanged. An eligible issue outside
the scope is not this run's to work, however long it has been waiting.

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
condition: **no eligible item remains in the target queue**. On the roadmap
queue that means the roadmap is finished and archived, or every unchecked
item left in it carries a `<!-- blocked: ... -->` annotation. On the issue
queue it means every open issue in scope is closed, assigned, or labelled
`agent:blocked`, `agent:needs-clarification`, or `epic`. An all-blocked queue is a
**terminating state, not a retry state**: the goal run does not re-attempt
blocked items to keep itself going, and it does not invent a triage pass
over them — `## The cycle` step 6's rule that blocked items wait for a
human holds here unchanged.

The loop cannot livelock, and here is the argument for why. Every
iteration ends in exactly one of two ways: either the dispatched item
**merges**, and the queue has one fewer open item — an unchecked roadmap
item, or an open issue; or the item exhausts its two attempts, gets
recorded blocked, and the queue has one fewer *eligible* item — the
annotation on `main`, or the `agent:blocked` label, is what makes the next
iteration's selection skip it. Both quantities are non-negative integers
over a finite item set, and both strictly decrease on every iteration that
produces them. There is no third outcome that leaves both unchanged. The
loop therefore reaches "no eligible item" in a bounded number of iterations
— at most as many as the queue has open items — and terminates.

As belt and braces, the goal run also keeps a **session-local record of
items it has exhausted during the run** and treats them as ineligible for
the remainder of the run, regardless of whether the blocked record landed
where it was aimed. This matters because step 6's push-as-a-race procedure
legitimately *drops* the annotation in two cases — the item was
independently checked off, or another actor already annotated it — and a
label edit can likewise fail against a tracker that is briefly unreachable.
While each of those outcomes happens to leave the item ineligible on the
next pass anyway, a termination argument that depends on a write having
succeeded is weaker than one that does not.

### Clearing the goal on an unsatisfied terminal state

When the loop terminates without the condition holding — the all-blocked
case, or any other case where the run ends with the target queue still
holding open work it cannot touch — issue `/goal clear` **itself**, before
stopping. The reason: in that state the condition is false and will stay
false, since nothing further is going to happen to this queue without a
human; a Stop hook left active would keep re-prompting a session that has
correctly concluded there is nothing left to do, forever. Report which
items are blocked and why as part of stopping — item references or issue
numbers — so a human can act without re-reading the queue.

When the condition **does** hold — the target roadmap is finished and
archived, or the issue queue holds nothing eligible in scope — rely on the
hook's own auto-clear instead; do not issue `/goal clear` in that case, and
do not treat it as required. The two terminal states are asymmetric on
purpose: one needs the skill to intervene, the other does not.

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
begins, until no eligible item remains in the target queue. The fallback
is not a second algorithm — it shares the target-selection rule, the
one-subagent guardrail, the attempt budget, and the termination condition
with the `/goal` path; the only thing missing is the hook, so the skill
supplies the repetition itself instead of relying on one.

### Completion handoff

A goal run finishes **one** target: one roadmap, or the issue queue at the
scope it was pinned to. If that target completes — the condition holds and
the hook clears — while other work is still eligible elsewhere, the run
ends there. A finished roadmap does not roll onto another roadmap, and an
exhausted issue scope does not roll onto a roadmap or onto a different
label. (The condition names one target, and re-issuing `/goal` with a
different condition mid-session is exactly what Setting the goal, above,
rules out.) The closing report names what still holds eligible work — the
roadmaps left, or the issues and labels left — and states the invocation
that would continue with the next one: `--goal` with no argument, `--goal
<next-slug>`, or `--goal <label>`, so a human who wants to keep going knows
the one command to type.

## Subagent dispatch

Dispatch a fresh subagent with a **self-contained** prompt — it shares no
context with this cycle, so hand it everything it needs rather than a
pointer back to the queue.

**On the issue queue**, the prompt carries:

- The issue's **number and title**, and its **body verbatim** — for Jira, its
  key, summary, and description.
- The reference `issue:<n>` — or `jira:<KEY-n>` on a Jira tracker — exactly
  as `arbor-auto-work` documents it, so
  it claims the issue, reads it in full including its comments, posts the
  intent contract as a comment before writing code, verifies the diff
  against it, and closes the issue out on merge.
- An instruction to run the `arbor-auto-work` skill in **autonomous mode —
  its default: no `--interaction`, no `--pr`.**

Pass `issue:<n>` (or `jira:<KEY-n>`), the one this cycle already resolved in
step 2 — never `issue:next` or `jira:next`, which would let the subagent select a different issue from the
one this cycle checked, will notify about, and is prepared to block.

**On the roadmap queue**, the prompt carries:

- The selected item's **full text**, verbatim — the why-plus-acceptance-
  criteria `arbor-auto-roadmap` requires each item to be phrased as.
- The item's reference in the form `roadmap:docs/roadmaps/<slug>.md#R<n>`,
  exactly as `arbor-auto-work` documents it, so it can validate the item and
  flip its checkbox on a successful commit.
- An instruction to run the `arbor-auto-work` skill in **autonomous mode —
  its default: no `--interaction`, no `--pr`.**

Never pass both references in one dispatch. `arbor-auto-work` permits an
issue that builds a roadmap item, but this skill selected from one queue and
holds bookkeeping for one queue; a second reference would close out work it
never selected.

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
`roadmap:` reference does not resolve, or the issue turns out to be closed,
already labelled, or locked by another cycle), and likewise a missing or
unrecognised value. Step 6's retry-then-record path is the correct response
in every one of those cases: the retry either clears a transient problem or
confirms the item genuinely cannot be built right now, and the blocked record
then stops that one item from stalling the queue.

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
  its file. **Roadmap queue only**: an emptied issue tracker fires nothing.

Name the item the way its queue does — `#<n>` for a GitHub issue, the key
(`SHOP-42`) for a Jira issue, the roadmap slug
and `R<n>` for a roadmap item — so the line identifies the work without a
lookup.

Merge-landed and roadmap-complete can both be true of the same cycle; when
they are, send both — neither replaces the other.

**Do not notify on dispatch**, and **do not notify on a quiet idle run** —
these are rules, not omissions. A subagent starting work is not yet an
outcome, and an hourly cron reporting "nothing to do" on every tick trains
the operator to ignore the channel, which then also buries the notifications
that actually matter.

If `PushNotification` is unavailable in this run's environment, continue
without failing the run — the merge on `main`, the blocked annotation or
`agent:blocked` label, the closed issue, and the archived roadmap file are
all durable records regardless of whether the notification itself was
delivered.

## Guardrails

- **Phases are strictly sequential.** A later phase is never worked while an
  earlier phase in the same roadmap still holds an unchecked item —
  blocked-annotated or not. A fully blocked earliest phase does not open the
  door to a later phase; it closes that roadmap for the cycle instead.
- **Exactly one subagent in flight at a time, never two.** A retry follows
  the first attempt sequentially, once it has finished; it never overlaps
  it.
- **At most two attempts per item per run** — one original plus one retry —
  on the same item, roadmap item or issue alike. A third attempt, in this
  run, is never made, and a different item is never picked up in its place
  within the same run.
- **Under `--goal`, that budget is per item, not per run.** A goal run spans
  many items across many cycles, so "per run" here reads as **per item**: at
  most two attempts — one original plus one retry — on the same item,
  however many other items the run has already worked. An item that
  exhausts its budget is recorded blocked and is thereafter skipped by
  selection, so it never gets a third attempt later in the same goal run
  either.
  This does not loosen the guardrail above; it says what "run" scopes to
  once a run can span more than one item.
- **Under `--goal`, "never move on to a different item in its place" is a
  within-cycle rule.** A cycle that exhausts its budget does not chain into
  a different item — it ends, recorded blocked. A goal run reaches its
  next item only by **starting a new cycle**, whose step-1 read of the
  pinned queue already sees that record; that is a new cycle selecting
  a new item, not a failed cycle picking a replacement, and it is how
  `## Foreground goal mode (--goal)` continues past a blocked item without
  contradicting this guardrail.
- **One run = one cycle — on the default, scheduled invocation.** Do not
  loop internally; exit as soon as the item is handled (merged, or
  blocked-and-recorded) or selection finds nothing eligible, and let the
  scheduler bring you back. The one exception is `--goal`
  (`## Foreground goal mode (--goal)`): when that flag was passed, this
  repetition is licensed — by the Stop hook on the `/goal` path, or
  in-session on the fallback — until the goal run's own termination
  condition (same section) is met.
- **One queue per cycle.** Detection picks the issue tracker or the roadmap
  files, and everything downstream — selection, dispatch, close-out
  observation, blocked bookkeeping — stays on that one queue. Never dispatch
  a cycle carrying both a tracker reference (`issue:` or `jira:`) and a
  `roadmap:` reference, and never
  record a block on the queue the item did not come from.
- **Repo-scoped, maintainer identity only.** Only ever touch branches,
  roadmap files, and issues in this repo — or, on a Jira tracker, in the one
  Jira project its config names — under the maintainer's own identity — no
  cross-repo activity.
- **Never author or re-scope issues.** Never open an issue — least of all to
  give yourself something to do on an idle tick — never edit an issue's
  title or body, never re-label one for priority, and never close one. The
  tracker's content is the developer's to write, exactly as the roadmap's
  is. Closing and the `agent:done` swap belong to `arbor-auto-work` inside
  its own close-out; this skill only observes that they happened.
- **Never author roadmap content.** Never write or edit an item's text,
  never add, remove, or rename a phase, never flip a checkbox in either
  direction, and never invoke `arbor-auto-roadmap`. The checkbox flip
  belongs entirely to `arbor-auto-work`, inside its own work commit — this
  skill does not flip one itself even when it observes a merge that plainly
  should have flipped one; an unflipped box after a merge is an upstream bug
  in the work cycle, not something to patch here.
- **The blocked record is the one exception, and it is bookkeeping, not
  authorship.** Appending `<!-- blocked: <reason> -->` to a twice-failed
  item's line, or adding `agent:blocked` and a failure comment to a
  twice-failed issue (clearing that issue's own stale `agent:working` with
  it), is the single write this skill ever makes to a queue. It records what
  happened to an item; it does not write what the item is. Being granted
  this one write licenses nothing else on the list above.
