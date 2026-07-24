---
name: arbor-auto-refine
description: Audit this repo's state and the running app to keep the issue backlog topped up with well-scoped, deduped work items — static doc/vision review, roadmap audit (docs/roadmap/ or GitHub Milestones written by arbor-auto-roadmap), dynamic app exploration for bugs, and triage of issues arbor-auto-developer left blocked. When the roadmap audit files an item's backlog issue, immediately flips that item's checkbox and closes the phase/roadmap out (archiving the file, or closing the Milestone and pinned tracking issue) — never waits for the issue to merge, and never invokes arbor-auto-roadmap itself; a roadmap is optional input, not a precondition. Run on a schedule (~every 8h); each run is a single pass, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.3"
---

# Arbor auto-refine agent

Agent 1 of the continuous dev loop (see `arbor-auto-developer` for agent 2). Each
run is a single pass: confirm a roadmap exists (creating one via
`arbor-auto-roadmap` if not), gather candidates from four sources, dedupe
against what's already open, file what's left (subject to a queue cap), then
exit. The `schedule` skill's cron cadence provides "keep polling" — this
skill does not loop internally.

## Setup (once, before the first scheduled run)

1. Confirm `gh auth status` works and note the repo
   (`gh repo view --json nameWithOwner`).
2. Confirm the labels `agent:backlog`, `type:dev`, `type:infra` (or the
   repo's own established types), `priority:1`, `priority:2`, `priority:3`
   exist (`gh label list`); if any are missing, that's a setup problem to fix
   before relying on the loop, not something to paper over per-run.
3. A roadmap (`docs/roadmap/*.md` or an open Milestone) is optional input, not
   a precondition — when none exists, the roadmap audit source (step 4)
   simply has nothing to contribute; every other source still runs. Roadmap
   content itself is always authored by `arbor-auto-roadmap`, and this skill
   never invokes it — planning the next roadmap is a human's call, made on
   their own schedule.
4. Confirm the integration branch `arbor-auto-developer`'s Setup already
   picked (`gh api repos/{owner}/{repo}/branches/<branch>`) — needed to commit
   docs-format roadmap bookkeeping (checkbox flips, archiving) directly to it
   in step 9. GitHub-format bookkeeping needs no branch at all.

## The cycle

You MUST create a todo per step and complete them in order.

1. **List open issues**
   (`gh issue list --state open --json number,title,body,labels`) — used for
   dedup in every source below, and to count the current `agent:backlog`
   queue depth.

2. **Roadmap check.** Check whether a roadmap exists: any non-archived
   `docs/roadmap/*.md` file, or any open Milestone. This is informational
   only — it decides whether step 4 has any candidates to contribute this
   run, not whether the run continues. If none exists, skip step 4 entirely
   and continue to step 3; never invoke `arbor-auto-roadmap` — planning the
   next roadmap is a human's call, on their own schedule.

3. **Static audit.** Read `CLAUDE.md`, `docs/CONVENTIONS.md`, `README.md`
   (product vision), the package boundaries, and `openspec/changes/archive/`
   (what's already shipped). Look for: documented behavior with no
   corresponding implementation, convention violations, and features the
   project's own stated vision implies but nothing tracks yet. No size
   ceiling — architecturally significant ideas are valid candidates too.

4. **Roadmap audit.** Skip this source entirely if step 2 found no roadmap.
   Otherwise, read the roadmap(s) found, per the format `arbor-auto-roadmap`
   defines. For each roadmap, find the earliest phase that still has any
   unchecked item — later phases in that same roadmap are not eligible this
   run, even if the queue has headroom. Unchecked items in that phase are
   candidates; when filed (step 8), each carries the `Roadmap:` reference line
   `arbor-auto-roadmap` defines, and (GitHub-format roadmaps only) gets
   assigned to that phase's Milestone. Filing is also where the item's
   checkbox gets flipped and, if warranted, the phase/roadmap closed out —
   see step 9.

5. **Dynamic exploration.** Bring up the project's e2e/agent stack (its
   `stack:e2e:up` script or equivalent — never the default profile). If the
   repo has an existing agentic/browser e2e harness, use it to interact with
   the running app:
   - First walk the fixed core journeys for this app (home page loads and
     navigation renders, key pages render their shell). Derive this list from
     what currently exists in the repo — check its routes/pages before
     assuming a fixed list is complete, and grow the list as the app grows.
   - Then spend remaining time on free-form exploration — click around, try
     edge cases, look for console errors or visibly broken UI.
   - Note anything broken or surprising as a candidate issue.
   - **Always tear the stack back down** before moving on, whether or not you
     filed anything.
   - If the stack fails to come up, **skip this source entirely for this
     run** and continue with the others — do not fail the run. Track
     consecutive stack-failure runs (e.g. a marker file, or check for your
     own prior "stack failed" issue comment) so you can tell a first failure
     (silent) from a second in a row (notify — see Notifications).

6. **Blocked-issue triage.** Among the open issues listed in step 1, find
   ones carrying an `arbor-auto-developer` comment explaining a second gate failure
   (see `arbor-auto-developer`'s retry-then-block behavior). Where the comment
   indicates the slice was too large or ambiguous, file a smaller,
   better-scoped follow-up issue and note the relationship in its body. Leave
   the original issue as-is — a human may still want to look at it.

7. **Dedup.** For every candidate gathered above, compare against the open
   issues from step 1 (title and body, not just exact string match — use
   judgment for near-duplicates). Drop any candidate that's already covered.

8. **File issues, respecting the cap.** Count currently-open `agent:backlog`
   issues. If already at or above 5, **file nothing this run** — send the cap
   notification (see Notifications) and stop. Otherwise, file candidates
   (highest-value first) up to the remaining headroom under the cap. Each
   filed issue:
   - Describes exactly one shippable slice (a "why" and acceptance criteria,
     sized like a single OpenSpec change).
   - Carries exactly the labels `agent:backlog`, one of `type:dev`/`type:infra`
     (or the repo's established equivalents), and one of
     `priority:1`/`priority:2`/`priority:3` (lower number = sooner; bugs
     found via exploration and blocked-issue re-scopes generally outrank
     brand-new feature ideas, but use judgment).
   - If it came from the roadmap audit (step 4), also carries the `Roadmap:`
     reference line `arbor-auto-roadmap` defines, and, for a GitHub-format
     roadmap, is assigned to that phase's Milestone.

9. **Close out refined roadmap items.** For every issue just filed in step 8
   that carries a `Roadmap:` reference line, flip that item's checkbox right
   away — don't wait for the issue to merge:
   - **Docs format:** edit the referenced `docs/roadmap/<file>.md`, checking
     `- [x] R<n>` for each newly-filed item. If every item in the file is now
     checked, `git mv` it to `docs/roadmap/archive/` in the same commit.
     Commit and push this directly to the integration branch confirmed in
     Setup — bookkeeping, not a new `arbor-auto-work` cycle. Batch every
     newly-filed item from this run into one commit.
   - **GitHub format:** PATCH the referenced Milestone's description (`gh api
     repos/{owner}/{repo}/milestones/<n>`) to check each newly-filed item's
     box. If every item in that Milestone is now checked, close it
     (`-f state=closed`). If that was the last open Milestone linked from the
     roadmap's pinned tracking issue, close the tracking issue too
     (`gh issue close`), leaving a closing comment that summarizes the
     phases.
   - If this closes out a whole roadmap (file archived, or tracking issue
     closed), send the roadmap-complete notification (see Notifications).

## Notifications

Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- The `agent:backlog` cap (5) is hit and no new issues were filed.
- The e2e stack has now failed to come up on two consecutive runs.
- Step 9 closes out a whole roadmap (file archived, or Milestone + tracking
  issue closed) — this is the signal that it's time for a human to plan the
  next one; there is no separate "no roadmap" notification since this skill
  never nags about a roadmap's absence.

Do **not** notify on a routine run that completes normally — that's noise,
not signal. If `PushNotification` isn't available in this run's environment,
leave a comment on the relevant issue instead and continue; don't fail the
run over a missing notification.

## Guardrails

- The roadmap audit source (step 4) only runs when a roadmap exists; its
  absence never blocks the static audit, dynamic exploration, or
  blocked-issue triage sources — those always run regardless.
- Only ever touch the project's e2e/agent profile — never the default
  profile.
- Never file more than the queue allows; the cap is a hard stop, not a
  suggestion.
- Never re-open or edit an issue you didn't file, except to add a triage
  follow-up reference or a stack-failure tracking marker.
- Never propose an item from a later roadmap phase while an earlier phase in
  that same roadmap still has an unchecked item.
- Never author new roadmap content — new phases, new items, or a new roadmap
  from scratch — that's `arbor-auto-roadmap`'s job, and this skill never
  invokes it. This skill only ever flips an existing item's checkbox and
  closes out a fully-refined file/Milestone/tracking issue that
  `arbor-auto-roadmap` already created.
- One run = one pass. Do not loop internally; exit when done and let the
  scheduler bring you back.
