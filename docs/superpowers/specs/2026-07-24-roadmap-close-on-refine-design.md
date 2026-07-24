# Roadmap closes at refinement, not at delivery

## Problem

A roadmap item's checkbox currently flips — and its file/Milestone/tracking
issue only closes — in `arbor-auto-developer`, at *merge* time. Between "issue
filed" and "issue merged" the roadmap still looks open, and a GitHub-format
roadmap's pinned tracking issue never closes at all (only individual
Milestones do, one per phase). Meanwhile `arbor-auto-refine` treats "no
roadmap exists" as a precondition failure for its entire cycle: it invokes
`arbor-auto-roadmap`'s interrogation every ~8h run, and if nobody answers, it
skips the whole pass — static audit, dynamic exploration, and blocked-issue
triage included, not just the roadmap-specific source. The result: a roadmap
whose items have already all been turned into backlog issues keeps getting
treated as active/incomplete, and the system nags for a new one (or goes
idle) every cycle even when there's nothing productive to do about it.

## Decision

A roadmap's job is to seed the backlog. Once every item has a filed issue,
that job is done — the roadmap closes immediately, regardless of whether the
issues have shipped yet. Delivery tracking continues on the issues themselves
(closed normally by `Closes #N` at merge); it's no longer the roadmap's
concern.

## Changes

### 1. Ownership and timing move to `arbor-auto-refine`

In `arbor-auto-refine`'s step 8 (File issues), for every issue filed this run
that carries a `Roadmap:` reference line, immediately flip that item's
checkbox in the same run, batched into one commit/API call per format:

- **Docs format:** edit `docs/roadmap/<file>.md`, check `- [x] R<n>` for each
  newly-filed item; if every item in the file is now checked, `git mv` it to
  `docs/roadmap/archive/` in the same commit. Commit and push directly to the
  integration branch (see #2) — bookkeeping, not a new `arbor-auto-work`
  cycle.
- **GitHub format:** PATCH the Milestone description to check each newly-filed
  item's box (`gh api repos/{owner}/{repo}/milestones/<n>`); if every item in
  that Milestone is now checked, close it (`-f state=closed`); if that was the
  last open Milestone linked from the roadmap's pinned tracking issue, close
  the tracking issue too, with a closing comment summarizing the phases. Pure
  `gh` calls, no commit needed.

`arbor-auto-developer` loses its "Roadmap mark-off" step entirely — the
description clause introducing it, the step-6 body text, the matching
notification bullet, and the guardrail about only flipping/closing what
`arbor-auto-roadmap` created. It goes back to only closing the GitHub issue
itself via its existing `Closes #N` commit trailer.

### 2. `arbor-auto-refine` gains commit access to the integration branch

New Setup step: confirm the same integration branch `arbor-auto-developer`'s
Setup already picks. `arbor-auto-refine` commits and pushes docs-format
roadmap bookkeeping directly to it, mirroring how `arbor-auto-developer` used
to do this same bookkeeping. GitHub-format closing needs no branch at all.

### 3. `arbor-auto-refine` never invokes the interrogation

Remove the "roadmap precondition" gate over the whole cycle. A roadmap's
existence only determines whether step 4 (roadmap audit) has anything to
contribute this run:

- No roadmap → step 4 contributes no candidates; steps 3, 5, 6 (static audit,
  dynamic exploration, blocked-issue triage) run exactly as normal.
- `arbor-auto-refine` never calls `arbor-auto-roadmap`. The old "no roadmap"
  notification (tied to a failed/declined interrogation) is removed — it no
  longer applies. The new "roadmap complete" notification (fired by
  `arbor-auto-refine` itself at close-out time, replacing developer's old
  merge-time version) is what signals a human to plan the next one.
- `arbor-auto-developer`'s self-seed step (3.2) drops its note about the
  self-seed pass possibly invoking `arbor-auto-roadmap`.
- `arbor-auto-roadmap` becomes purely user-invoked. Its description and intro
  drop the "`arbor-auto-refine` invokes it as a precondition fix-up" clause.

### 4. Contract update in `arbor-auto-roadmap`

The "Roadmap: reference line" shared-contract section is rewritten: the
checkbox means "refined into the backlog," not "shipped." The owner of
flipping/closing is now `arbor-auto-refine`, not `arbor-auto-developer`.
Phase-sequencing ("earliest phase with an unchecked item" gates which phase's
items `arbor-auto-refine` may propose) is unchanged in mechanism — only what
"checked" means shifts, from merged to filed.

## Out of scope

- No change to `arbor-auto-work`, issue labels, the backlog cap, or dedup
  logic.
- No change to how `arbor-auto-roadmap` interrogates or generates a roadmap —
  only to who reads/closes it afterward.
- No dual-status (refined vs. shipped) tracking on individual items; a single
  checkbox now means "refined."
