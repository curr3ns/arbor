---
name: arbor-auto-developer
description: Poll for feedback on the integration branch's pull request (unresolved review comments, failing CI) first, then the issue backlog, implementing the highest-priority item one at a time via arbor-auto-work --autonomous overridden to integrate against a dedicated integration branch instead of the default branch. Keeps a single running PR from the integration branch to the default branch up to date for human review. Never touches roadmap content — arbor-auto-refine flips a roadmap item's checkbox and closes it out at filing time, not this skill at merge time. Self-seeds the backlog with one arbor-auto-refine pass when the queue is empty and there's no PR feedback to address. Run on a schedule (~hourly — the schedule skill's cron has a 1h minimum interval); each run is a single cycle, not a loop.
license: MIT
metadata:
  author: arbor
  version: "1.4"
---

# Arbor auto-developer agent

Agent 2 of the continuous dev loop (see `arbor-auto-refine` for agent 1). Each
run is a single cycle: react to feedback on the integration branch's PR if
there is any, otherwise pick one issue, dispatch one subagent to handle it,
record the outcome, exit. If the issue queue starts empty (and there's no PR
feedback to address), the run also self-seeds with one `arbor-auto-refine` pass
before picking — that's still part of the same one cycle, not a second loop.
The `schedule` skill's cron cadence provides "keep polling" — this skill does
not loop internally, and never runs two subagents at once.

## Setup (once, before the first scheduled run)

1. Confirm `gh auth status` works and note the repo
   (`gh repo view --json nameWithOwner`).
2. **Pick the integration branch** — a branch distinct from the repo's
   default branch (e.g. `develop`) that every autonomous merge targets
   instead, so this loop never merges to the default branch directly.
   Confirm it exists (`gh api repos/{owner}/{repo}/branches/<branch>`). If
   the repo has no such branch yet, that's a setup decision to make
   explicitly before relying on the loop — create one, or don't enable this
   skill for a repo where merges must go straight to the default branch.
3. Confirm the `arbor-auto-work` skill is present and working.

## The cycle

You MUST create a todo per step and complete them in order.

1. **Check the integration branch's PR.** Look for an open PR from the
   integration branch into the default branch, authored under this loop's
   identity:
   ```bash
   gh pr list --head <integration-branch> --base <default-branch> \
     --author "@me" --state open --json number,reviews,reviewDecision
   ```
   If one exists:
   - **P0 — PR feedback.** Unresolved review threads
     (`gh api repos/{owner}/{repo}/pulls/<n>/comments`) and
     `CHANGES_REQUESTED` reviews. Ignore resolved threads and plain
     approvals.
   - **P1 — failing CI.** Any failing checks on that PR (`gh pr checks <n>`).

   If P0 or P1 has anything actionable, go to step 2 (PR feedback path) and
   skip the issue queue entirely this cycle. Otherwise skip to step 3 (issue
   queue path).

2. **Address PR feedback (P0/P1 path).** Dispatch exactly one subagent:
   check out the integration branch, address every listed review comment /
   fix the failing checks, run the project gate, push. Then **reply to and
   resolve** each addressed review thread so it is not reprocessed next
   cycle. Do not touch resolved threads or approvals. Send the
   feedback-addressed notification (see Notifications) and end the run here
   — do not also touch the issue queue in the same cycle.

3. **Issue queue (P2 path) — only reached when step 1 found no PR or no
   actionable feedback on it.**
   1. **List open issues**
      (`gh issue list --state open --json number,title,body,labels`).
   2. **Self-seed if empty.** If the queue is empty, run the `arbor-auto-refine`
      skill for exactly one pass (in-process — no subagent dispatch needed),
      then re-list open issues. Never invoke `arbor-auto-refine` a second
      time in the same run, regardless of what the one pass finds. If the
      queue is *still* empty after that one pass, **end the run now** — no
      dispatch, no notification, nothing else to do until the next scheduled
      tick.
   3. **Order by priority.** Sort by the `priority:*` label — `priority:1`
      first, then `priority:2`, then `priority:3`; issues with no
      `priority:*` label sort last.
   4. **Select the single highest-priority issue.**
   5. **Dispatch exactly one subagent** (see Subagent dispatch below) and
      wait for it to finish. Never dispatch a second subagent while one is in
      flight.
   6. **On success:** the subagent's merge closes the issue via its
      `Closes #N` commit trailer once the integration branch itself reaches
      the default branch — verify the merge landed on the integration branch
      (`git log <integration-branch> --oneline -1` or equivalent). Then
      **ensure the running PR exists**: if no open PR from the integration
      branch to the default branch exists yet, open one now (title
      summarizing the batch, body listing accumulated work); if one already
      exists, its diff updates automatically from the push — nothing further
      to do. Send the merge-landed notification. This skill never touches
      roadmap content — if the issue carried a `Roadmap:` reference line,
      `arbor-auto-refine` already flipped that checkbox (and closed out the
      phase/roadmap, if warranted) back when it filed the issue.
   7. **On gate failure:** dispatch exactly one retry subagent in a fresh
      context, passing the failure output. If the retry also fails, leave
      the issue open, post a comment on it explaining the failure (what
      broke, at which gate step), send the blocked notification, and stop —
      never a third attempt on the same issue in the same run (blocked
      issues wait for `arbor-auto-refine`'s triage or a human).

## Subagent dispatch

Dispatch a fresh subagent with a self-contained prompt containing the full
issue body and number, and these explicit instructions:

- Run the `arbor-auto-work` skill in **autonomous** mode (its default — no
  `--interaction`, no `--pr`) for this issue's slice of work.
- **Override the integration branch to the branch chosen in Setup, not the
  repo's default branch**: branch off it (not off whatever `arbor-auto-work` would
  otherwise default to), and the final merge target is it. This is a
  per-dispatch instruction to the subagent, not a change to `arbor-auto-work`
  itself — `arbor-auto-work` run directly by a human still defaults to the repo's
  default branch.
- Include a `Closes #<issue-number>` trailer in the commit message so GitHub
  closes the issue once that commit reaches the default branch.
- Return a compact result:
  `{ outcome: shipped | blocked | failed, work_id, branch, note }`.

## Notifications

Send a `PushNotification` (one line, under 200 chars, leading with what's
actionable) when:
- A dispatched subagent's merge lands on the integration branch.
- PR feedback (review comments or failing CI) was addressed and pushed.
- An issue is left blocked after a second failed attempt.

Do **not** notify when dispatching (only on the outcome), and do not notify
for a routine successful run beyond the pings above. If `PushNotification`
isn't available in this run's environment, rely on the issue comment
(blocked case), the resolved review thread (PR-feedback case), or the
closed-issue state (success case) and continue; don't fail the run over a
missing notification.

## Guardrails

- Sequential only: exactly one subagent in flight at a time.
- Never invoke `arbor-auto-refine` more than once per run, even if the queue is
  still empty afterward.
- Never merge into the repo's default branch — every dispatch merges into
  the integration branch chosen in Setup. The loop may open or update a PR
  from the integration branch to the default branch for human review, but
  only a human merges that PR.
- At most one open PR from the integration branch to the default branch at a
  time — reuse it, never open a second.
- Never touch roadmap content in any form — no checkbox, file, Milestone, or
  tracking issue. That's entirely `arbor-auto-refine`'s job now, done at
  issue-filing time.
- P0/P1 (PR feedback) always takes priority over the issue queue in a given
  cycle — never pick up a new issue while there's unaddressed feedback on the
  running PR.
- Never make more than 2 attempts (1 original + 1 retry) on the same issue,
  or the same round of PR feedback, in a run.
- One run = one cycle. Do not loop internally; exit when done (or idle) and
  let the scheduler bring you back.
- Only ever touch issues/branches/PRs in this repo, under the maintainer's
  own identity — no cross-repo activity.
