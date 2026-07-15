---
name: arbor-loop
description: Run a repo autonomously and continuously — a persistent conductor that repeatedly grabs the highest-priority slice of work (PR review comments, failing CI, then roadmap items and issues), dispatches a fresh subagent to implement it via arbor-work and open a pull request, and loops. Prioritizes fixing PR feedback, sleeps through token-limit resets, and re-polls when idle. Pass --merge to skip PRs and have subagents merge directly to the default branch. Use to maximize unattended progress on a repo.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor loop — autonomous work conductor

Turns the current session into a **conductor**: a persistent in-session loop
that repeatedly selects one slice of work and dispatches a **fresh subagent** to
implement it. Each slice starts with clean context because it runs in its own
subagent; the conductor only ever receives a short structured summary back, so
its own context stays small across many slices.

The conductor **plans and orchestrates only** — it never edits code directly and
never merges. All implementation happens inside subagents via `arbor-work`.

## Inputs / flags

- `--once`: run a single cycle, then stop (for testing).
- `--max-slices N`: stop after N slices ship.
- `--idle-minutes M`: how long to sleep before re-polling when the queue is
  empty (default 5).
- `--merge`: dispatch subagents with plain `arbor-work` (gate → **merge** to the
  default branch) instead of `arbor-work --pr`. No PRs are opened, so the **P0
  (PR feedback)** and **P1 (failing CI)** queue sources are skipped and the queue
  collapses to **P2** (roadmap + issues). Trades away the human review gate for
  speed — use only on a repo where you fully trust the project gate. Default
  (without this flag) is PR mode: every slice ends at *push + open PR*, and
  humans merge.

## Data model — `.docs/roadmap/`

The living roadmap mirrors the OpenSpec change lifecycle:

```
.docs/roadmap/
  RM-1-add-backoff.md      # active items — one shippable slice each
  RM-2-cache-tokens.md
  archive/                 # completed items are moved here
```

Each item is one shippable slice (≈ one OpenSpec change / one PR):

```markdown
---
id: RM-3
title: Add rate-limit backoff to the API client
priority: 2          # lower = sooner
status: ready        # ready | in-progress | blocked | done
depends_on: [RM-1]   # optional; branch off that work if it is still unmerged
type: DEV            # DEV | INFRA — feeds arbor-work's work ID
---

## Why
...
## Acceptance
- [ ] ...
```

**The conductor is the only writer of `status`.** The human may freely add,
remove, reorder, or edit any other field while the loop runs — the conductor
re-reads the directory every cycle and picks up the changes. If `.docs/roadmap/`
does not exist and the user wants a roadmap source, create it with a first item
before looping.

## Setup (once, before looping)

You MUST create a todo for each setup item.

1. **Identify the loop's git user** — the `user.name` / `user.email` in effect.
   The conductor only ever touches PRs and branches owned by this user.
2. **Confirm `gh` works** (`gh auth status`) and note the repo's default branch
   (usually `main`).
3. **Read `.docs/roadmap/`** (active items only) into memory, and the repo's
   conventions (`CLAUDE.md`, `docs/CONVENTIONS.md`) if present.

## The cycle

Repeat until a stop condition (see Stopping). You MUST create a todo per step.

**Every cycle — and every wakeup from idle or a token-limit sleep — starts by
re-polling P0 PR feedback before any roadmap work.** Never continue rolling
through `.docs/roadmap/` items across slices without first rebuilding the queue
from PR comments and CI. A roadmap item is only selected when there is no
outstanding P0/P1 work. In `--merge` mode no PRs exist, so P0/P1 are always empty
and the queue is P2 only — skip the P0/P1 polling entirely.

1. **Build the queue** from three sources, in strict priority order:
   - **P0 — PR feedback.** For each open PR authored by the loop's git user,
     find unresolved review threads and `CHANGES_REQUESTED` reviews:
     ```bash
     gh pr list --author "@me" --state open --json number,headRefName,title
     gh pr view <n> --json reviews,reviewDecision
     gh api repos/{owner}/{repo}/pulls/<n>/comments   # review threads
     ```
     Ignore resolved threads and plain approvals.
   - **P1 — failing CI.** For those same PRs, any failing checks:
     ```bash
     gh pr checks <n>
     ```
   - **P2 — new work.** `ready` items in `.docs/roadmap/` plus open issues
     (`gh issue list --state open`), ordered by `priority`, then by
     dependency-readiness.
2. **Select** the single highest-priority actionable item. Skip any P2 item
   whose `depends_on` references an item whose `status` is `blocked`.
3. **Decide the base branch:**
   - P0 / P1 → check out the existing PR branch.
   - P2 whose `depends_on` points at an **unmerged** item → branch off that
     item's branch.
   - Otherwise → branch off the default branch.
4. **Mark the item `in-progress`** (P2 roadmap items only).
5. **Dispatch one subagent** (see Subagent dispatch) and wait for it. One at a
   time — never run slices in parallel.
6. **Record the outcome** the subagent returns, update the item's `status`
   (archive on `shipped`, `blocked` on repeated failure), and **log one line**:
   `slice <id> → <outcome> <pr_url>`.
7. Loop.

## Subagent dispatch

Dispatch a fresh subagent with a self-contained prompt containing: the selected
item (or PR + the exact comments/CI to address), the base branch to start from,
the priority reason, and the required return shape. Instruct it to:

- **P2 (new work):** run the `arbor-work` skill for this slice — autonomous. In
  the default PR mode, pass `--pr` so it ends at *push + open PR*, never merging.
  In `--merge` mode, run plain `arbor-work` (no `--pr`) so it runs the gate and
  **merges** to the default branch; there is no `pr_url` to return.
- **P0 / P1 (feedback / CI):** check out the PR branch, address every listed
  comment / fix the failing checks, run the project gate, push. Then **reply to
  and resolve** each addressed review thread so it is not reprocessed next cycle.
  Do not touch resolved threads or approvals.

The subagent MUST return only this compact result (no prose):

```
{ outcome: shipped | blocked | failed, work_id, pr_url, branch, note }
```

## Token limits — react to the actual rate-limit failure

Claude Code does not expose remaining usage or the reset time to the model: no
tool, environment variable, or hook reports it (it is shown only to the human,
via `/usage`). So the conductor does **not** try to predict or measure the
limit. Instead it simply keeps working until a request actually fails with a
rate-limit error, then waits and resumes:

- When a slice (or the conductor itself) hits a rate-limit / usage error, **stop
  starting new slices** and `ScheduleWakeup` on a coarse cadence — try the error
  message's reset time if one is present, otherwise back off roughly hourly.
- On each wake, attempt one lightweight cycle — which, like every cycle, begins
  by re-polling P0 PR feedback. If it still fails with a limit error, sleep
  again; once the window has reset the cycle succeeds and normal looping resumes.
- **No committed work is lost.** `arbor-work` commits and pushes before the
  subagent returns, so a hard block mid-slice at worst discards one uncommitted
  slice, which is retried after the reset.

`--max-slices N` remains available to bound a run deliberately, and running the
loop as a scheduled cloud agent / cron keeps start times outside the session so
a rate-limited run simply ends and the next scheduled run resumes after reset.

## Failure handling — self-resolve, then block

When a slice fails (gate fails, subagent error, merge conflict):

1. **Retry once** in a fresh subagent, passing the failure context so it can
   self-resolve.
2. Only if it still cannot complete on the **second attempt**, mark the item
   `blocked` with a note, leave its branch/PR intact for human inspection, and
   move on.

Never make more than 2 attempts in a row on the same item.

## Idle — sleep and re-poll

When the queue is empty (no PR feedback, no failing CI, no ready items or open
issues), sleep for `--idle-minutes` via `ScheduleWakeup`, then re-poll —
starting with P0 PR feedback. New PR comments, CI results, and issues get picked
up on the next cycle. Continuous by default.

## Stopping

Stop and report a summary when: `--once` completes one cycle, `--max-slices` is
reached, or the user interrupts. Otherwise the loop runs continuously, sleeping
through resets and idle periods.

## Guardrails

- Only ever touch PRs/branches owned by the loop's git user.
- Re-poll P0 PR feedback (and P1 CI) at the start of every cycle and every
  wakeup — never roll through roadmap items without re-checking PR comments.
- The conductor never edits code and never merges directly — subagents do the
  work. In PR mode `arbor-work --pr` opens PRs and humans merge; in `--merge`
  mode the subagent's `arbor-work` performs the merge.
- Never start a slice whose `depends_on` is `blocked`.
- Sequential only: exactly one subagent in flight at a time.
- One change = one work ID = one branch = one PR (inherited from `arbor-work`).
