---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work — take the intent, assign a work ID, branch, plan the slice into acceptance criteria and tasks, implement it, gate on the project's verification command, verify the diff against the intent, commit, push, and integrate. Use when starting or completing any non-trivial change. Each phase runs as a subagent under a per-phase model (defaults plan=opus, work=sonnet, gate=haiku), overridable with plan:/work:/gate: tokens, plus its own review: token for the intent gate, an optional roadmap: item reference this cycle closes out on commit, and an optional issue: reference (a number, or issue:next to select one) making a GitHub issue the cycle's contract — claimed, verified against, and closed on merge. Defaults to autonomous; pass --interaction to run with approval prompts, or --pr to run autonomously but open a pull request instead of merging.
license: MIT
metadata:
  author: arbor
  version: "3.0"
---

# Arbor work cycle

The required process for all non-trivial work in a repo: work ID, branch, plan,
implement, gate, intent gate, commit, push, integrate. Two modes:

- **autonomous** (default): proceed through every step without prompts; merge to
  `main` at the end. Pass `--pr` to end by pushing and opening a pull request
  instead of merging — still no prompts.
- **interactive** (`--interaction`): ask for approval before implementing and
  before integrating; open a pull request at the end instead of merging.

The work is **implemented directly**. There is no proposal-then-apply ceremony
and no spec artifacts to author or archive — the plan in step 4 lives in the
session and is threaded into the implementation, the code is the deliverable, and
the record of what changed and why lives in the commit and the pull request.

## The two gates

Everything here serves two gates. Both must pass before an integration.

1. **The verification gate** — the project's verification command passes in full,
   run at step 6. This proves the code _works_.
2. **The intent gate** — the shipped diff satisfies every acceptance criterion of
   the work source, checked at step 7. This proves the code is _the thing that
   was asked for_.

A green verification gate on work that misses the intent is a **failed cycle**,
not a successful one. In an autonomous repo the intent gate is what stands in for
human review, so run it honestly and adversarially: if you cannot point at the
code that satisfies a criterion, that criterion is not satisfied.

## Autonomy

Merge without approval. Close without approval. That is the intended design, not
a shortcut. Make reasonable assumptions and pick sensible best-practice defaults
on your own. Escalate (see `## Escalation and stop`) only when an ambiguity has
**no defensible default** — where two readings lead to materially different
software and picking wrong wastes the whole cycle — or when a blocker is one you
genuinely cannot clear. When you do escalate, ask the specific question; never
hand back the whole decision.

## Inputs

A short description of the slice of work, and optionally the type (`DEV` for
development — the default — or `INFRA` for infrastructure), mode (`--interaction`
or `--pr`), per-phase model tokens (`plan:`/`work:`/`gate:`, bare or behind
`--models`), a `review:` model for the intent gate, a roadmap item reference
(`roadmap:docs/roadmaps/<slug>.md#R<n>`, the format `arbor-auto-roadmap` defines)
naming the roadmap item this cycle is building, and an issue reference
(`issue:<n>`, or `issue:next` to select one) naming the GitHub issue this cycle
is building.

The roadmap and issue references are both optional and independent: omitting both
runs the cycle unchanged — no flip, no claim, no close-out, no error.

## Model selection

Every phase runs as a subagent dispatched with an explicit `model`. The four
accepted model names are exactly the Agent tool's `model` values — `opus`,
`sonnet`, `haiku`, `fable` — passed straight through; the skill never resolves
concrete model ids itself. Each phase has a default tier, used when the caller
does not override it:

| Knob      | Phase                                     | Default    |
| --------- | ----------------------------------------- | ---------- |
| `plan:`   | plan the slice (step 4)                   | **opus**   |
| `work:`   | implement the slice (step 5)              | **sonnet** |
| `gate:`   | run the project's verification command    | **haiku**  |
| `review:` | the intent gate (step 7)                  | **opus**   |

`review:` defaults to opus because the intent gate is the judgement call that
replaces human review.

**Syntax.** Bare tokens (primary) or a `--models` list — both parse identically:

```
<description> plan:opus work:sonnet
<description> --models plan:opus,work:sonnet
```

**Parsing.**

- A token matching `^(plan|work|gate|review):(opus|sonnet|haiku|fable)$` — or a
  comma-separated list of them behind `--models` — is a model assignment and is
  removed from the input.
- After removing model tokens, the `--interaction`/`--pr` flags, and any
  `roadmap:`/`issue:` token, whatever remains is the work description.
- An **unknown phase key or model name** (e.g. `wrok:sonnet`, `plan:opua`) is a
  hard error: **stop and report** it. Never silently ignore a mistyped override
  or fall back to a default in its place.
- Unspecified phases use their default tier from the table above.

Dispatch every phase **synchronously** (`run_in_background: false`) — each phase
depends on the previous one's output and file changes. Subagents share this
working directory, so the implementation phase sees the plan's context and the
gate sees the implementation's edits.

## Work sources

Three ways a cycle learns what to build. They differ only in where the intent
comes from and what is closed out at the end; steps 2–6 and 9 are identical in
all three.

| Source                | Intent contract is…                                            | Closed out by…                                 |
| --------------------- | -------------------------------------------------------------- | ---------------------------------------------- |
| `issue:<n>`           | the issue body and its comments, restated as a contract comment  | `Closes #<n>` plus the label swap in step 10   |
| `roadmap:…#R<n>`      | the item's why-plus-acceptance-criteria text, verbatim            | the checkbox flip and commit bullets in step 8 |
| neither (description) | the description, made concrete by the plan written in step 4     | nothing beyond the commit                      |

Whichever applies, that source's acceptance criteria are what the intent gate at
step 7 checks the diff against. Passing both `issue:` and `roadmap:` is allowed —
an issue that builds a roadmap item — and both close-outs then run.

## Steps

You MUST create a todo per step and complete them in order.

0. **Split off model, roadmap, and issue tokens.** Set aside any
   `plan:`/`work:`/`gate:`/`review:` tokens (bare or behind `--models`), the
   `--interaction`/`--pr` flags, any `roadmap:` token, and any `issue:` token.
   Reject an unknown phase key or model name with a hard error — stop and report,
   before any branch is created or any issue is claimed. Fill unspecified phases
   with their defaults (plan=opus, work=sonnet, gate=haiku, review=opus) and hold
   the resolved model map for the dispatches below. What remains is the work
   description used everywhere below. Keeping all of them out now ensures none
   leaks into the work-ID slug in steps 2–3.

   **Preconditions.** Before touching anything: the working tree is clean
   (`git status --porcelain` is empty), you are on the default branch, and it is
   up to date (`git pull --ff-only`). In issue mode, `gh auth status` must also
   succeed. Any failure stops the run here.

   If a `roadmap:` token was supplied, resolve and validate it now, before the
   branch is created in step 3: `docs/roadmaps/<slug>.md` must exist, it must
   contain an item with the given `R<n>`, and that item's box must be
   `- [ ]`. Each of the following is a hard error that stops the run — never
   create the file, append the item, fall back to another item, or downgrade
   any of them to a warning or a silent skip: the file does not exist (this
   includes a reference into an already-archived roadmap — resolve it as
   missing, never search `docs/roadmaps/archive/` for the item); the file
   exists but has no item with that `R<n>`; the item exists but its box is
   already `- [x]`.

   If an `issue:` token was supplied, resolve and **claim** the issue now, also
   before the branch exists. First check the lock — no other cycle may hold one:

   ```bash
   gh issue list --label "agent:working" --state open
   ```

   If that returns an issue, another cycle owns it. Either resume that issue (its
   branch exists and no other process is live) or stop. Never run two cycles at
   once. Then resolve the reference:

   - `issue:<n>` — use that issue. It must be open, must not be a pull request,
     and must not carry `agent:blocked` or `agent:needs-clarification`. Each of
     those is a hard error that stops the run.
   - `issue:next` — select the first eligible issue: open, not a pull request,
     not labelled `agent:blocked` or `agent:needs-clarification`, unassigned,
     ordered by priority label `p0` > `p1` > `p2` > unlabelled, then oldest
     `createdAt`.

     ```bash
     gh issue list --state open --limit 50 \
       --json number,title,labels,assignees,createdAt,body
     ```

     If nothing is eligible, say so and stop. Do not invent work, and never
     author an issue to give yourself something to do — issue content is the
     developer's to write.

   Claim it before any other action, so a concurrent run cannot pick the same one:

   ```bash
   gh issue edit <n> --add-label "agent:working" --add-assignee @me
   ```

1. **Determine the slice, and state the intent contract.** Restate the smallest
   shippable unit of work. If it's too big for one change, stop and split it.

   In issue mode, read the issue in full, **including every comment**, then
   answer three questions: what changes, and for whom; what the observable
   acceptance criteria are (each checkable — an input and an output, a visible
   behaviour, an error case; "works well" is not a criterion); which packages it
   touches, and whether any dependency edge changes (a new edge that creates a
   cycle is a design error and needs justifying up front). If a question is
   unanswerable by any defensible assumption, escalate and stop.

   Otherwise post the intent contract as an issue comment **before writing code**:

   ```bash
   gh issue comment <n> --body "..."
   ```

   It states, in this order: what you are building; the numbered acceptance
   criteria you will verify against; every assumption you made and why; anything
   explicitly out of scope for this cycle. This comment is what the intent gate
   checks against at step 7, and it gives the developer a window to correct
   course asynchronously without blocking the loop.

   In roadmap mode the item's own text is the contract — it is already phrased as
   why-plus-acceptance-criteria — so restate it in the session rather than
   writing it anywhere. Never edit the roadmap to record it.

2. **Assign the work ID.** Type is an **uppercase** `DEV` (default), `INFRA`, or
   another established uppercase type. The next number is one more than the
   highest existing ID of that type across the repo's commit history and its
   branches:

   ```bash
   { git log --all --pretty=%s; git branch -a --format='%(refname:short)'; } \
     | grep -oE '\b[A-Z]+-[0-9]+\b' | sort -u -t- -k2 -n
   ```

   Form the work ID `<TYPE>-<n>-<slug>`: uppercase type prefix, lowercase
   kebab-case slug (e.g. `DEV-4-add-cart`). It is assigned this way in every
   mode: an issue number is a reference the cycle carries, never the work-ID
   counter, so `issue:42` does not make the work ID `DEV-42-<slug>`.

3. **Create the branch** `feature|bugfix|hotfix/<id>-<slug>` (feature for
   features, bugfix for fixes, hotfix for hotfixes), e.g.
   `feature/DEV-4-add-cart`.

4. **Plan the slice (plan model).** Dispatch a subagent with `model` = the
   **plan** model. Give it the work description, the work source's contract from
   step 1, and the repo's conventions if documented (`CLAUDE.md`,
   `docs/CONVENTIONS.md`). Ask it to read enough of the codebase to plan against
   what is actually there, then return, **as text in the session**:

   - the numbered **acceptance criteria** the finished work must satisfy, each
     one observable and checkable;
   - a concrete **task list** — the ordered changes to make, named by file or
     module, small enough that each is individually verifiable;
   - the **edge cases and error paths** that matter, and any design decision it
     had to make, with the reason.

   **It writes no files.** No proposal, no spec, no tasks file — the plan is
   session state that step 5 consumes and step 7 checks against. Where the work
   source's acceptance criteria and the plan diverge, the work source wins.

   Hold the returned plan; every later step refers back to it.

5. **Implement (work model).** If `--interaction`, summarize the plan and ask for
   approval before dispatching. Then dispatch a subagent with `model` = the
   **work** model, carrying the full plan from step 4 verbatim and the **Code
   standards** section below verbatim — the subagent never reads this file.

   It implements **every** task completely and to a production standard: the code
   must genuinely satisfy the requested slice end-to-end — not merely compile or
   pass a token test — handling the obvious edge cases and error paths, and
   following the repo's conventions if present: narrow directories, concise
   self-documenting files, reuse over duplication, extension over rewrite, tests
   beside source. The bar is work that genuinely satisfies the slice, not work
   that moves through the steps.

   Stay inside the slice's scope. Unrelated problems you notice are follow-up
   work to report at step 10, not extra commits on this branch. If the phase hits
   a genuine blocker — an ambiguous task, an error it cannot clear — it reports
   that back instead of a clean completion; treat that as a real problem and stop
   rather than continuing to the gate.

6. **Run the gate (gate model).** If the project defines a verification command —
   an `npm run gate` / test / lint / build script, or a gate documented in the
   repo — dispatch a subagent with `model` = the **gate** model to run the
   **full** gate, not a convenient subset, and report its outcome faithfully. It
   MUST pass end-to-end; do not proceed otherwise. A genuine failure is a real
   defect to surface and fix, never something to work around or paper over. If
   the repo defines no such command, note that and continue.

   Some gates distinguish a stage's outcome into more than plain pass/fail —
   e.g. an e2e/integration stage that can report the environment itself was
   unreachable (no daemon, registry egress blocked, stack never came up)
   separately from the suite actually running and failing. When the gate makes
   that distinction, handle the three outcomes differently:

   - **Passed for real:** proceed; no note needed.
   - **Environment-blocked** (the stage never actually ran against real
     infrastructure): the cycle MAY proceed, but you MUST record the reason and
     surface it in the commit at step 8 and in the pull request or merge note at
     step 10. Never treat it as a shortcut.
   - **Genuine failure** (the stage ran and failed): a real implementation
     problem, never reclassified as environment-blocked — go back to step 5 to
     fix it, then re-run this gate.

   A genuine gate failure stops the cycle here; do not continue to the intent
   gate or the commit on a red gate.

7. **The intent gate.** Dispatch a **fresh subagent** that did not do the
   implementation, under the `review:` model (default opus). Give it exactly two
   things: the work source's contract — the issue body plus the intent-contract
   comment, or the roadmap item's verbatim text, or the work description plus the
   plan from step 4 — and the branch diff (`git diff <default-branch>...HEAD`).

   Ask it to return a verdict per acceptance criterion — `satisfied` with the
   file and line that satisfies it, or `not satisfied` with what is missing —
   plus any change in the diff that no criterion asked for. Instruct it to
   default to `not satisfied` when it cannot find the evidence.

   - **Any criterion unmet** → back to step 5 to finish the work, then re-run the
     verification gate and this gate. Do not commit and do not open a pull
     request on an unmet criterion.
   - **Unrequested scope in the diff** → remove it, or justify it at step 10 as
     necessary to the change (a refactor the fix required, a test a criterion
     implies).

   Hold the verdict table: step 10 puts it in the pull request body or the
   closing comment.

8. **Commit.** If a valid `roadmap:` reference was supplied, flip the item
   before authoring the commit — reaching this step is itself the
   precondition, since a genuine gate failure already stopped the cycle at
   step 6 and an unmet acceptance criterion already stopped it at step 7.
   Re-confirm the target line is still `- [ ] **R<n>**`, then change only that
   marker to `- [x] **R<n>**`, leaving the item's text and wrapped
   continuation lines byte-identical. Then test the whole file: if no
   `- [ ] **R<m>**` line survives for any item `<m>` — not just the one you
   flipped — the roadmap is complete, so create `docs/roadmaps/archive/` if it
   isn't there yet and `git mv` the file into it; the flip already landed, so
   the archived copy carries the checked box. If any item is still unchecked,
   leave the file at `docs/roadmaps/<slug>.md`. Stage the flip and any move
   into the same commit as the work, on the same branch — no separate
   bookkeeping commit or push.

   Commit with a subject `{ticket} {short description}` (uppercase work ID,
   e.g. `DEV-4 add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented. If step 6
   reported an environment-blocked stage — which still reaches the flip and
   any archival above — add a bullet surfacing it, e.g. `- E2E skipped:
   environment-blocked (<reason>); not independently verified.` If a
   `roadmap:` reference was supplied, add `- Roadmap: <slug> R<n> complete`
   (`<slug>` is the roadmap filename without its `.md` extension); if the flip
   also archived the file, additionally add `- Roadmap <slug> complete;
   archived`. If an `issue:` reference was supplied **and this cycle ends in a
   merge** (autonomous, no `--pr`), add a `Closes #<n>` line so the merge to the
   default branch closes the issue; when the cycle ends in a pull request
   instead, `Closes #<n>` belongs in the PR body at step 10, not here. All of
   these bullets are independent and may appear together in one commit body.

9. **Push** the branch.

10. **Integrate and close out.** Autonomous: merge to `main` — unless `--pr` was
    passed, in which case push and open a pull request instead of merging.
    Interactive: ask for approval, then open a pull request. Where the repo ships
    a pull request template, fill it; otherwise the body carries `Closes #<n>` in
    issue mode, the step 7 verdict table mapping each acceptance criterion to the
    code that satisfies it, the gate evidence from step 6 (including any
    environment-blocked stage and its reason), and the assumptions from the
    intent contract.

    If a merge conflicts, rebase onto the default branch, then re-run **both**
    gates — step 6's verification gate in full and step 7's intent gate — before
    merging. A rebased branch is unverified until it is re-gated.

    In issue mode, close out once the work has landed:

    ```bash
    git switch main && git pull --ff-only
    gh issue view <n> --json state   # confirm Closes #<n> actually closed it
    gh issue close <n>               # only if it did not
    gh issue edit <n> --remove-label "agent:working" --add-label "agent:done"
    gh issue comment <n> --body "..."  # PR/commit link, criteria table, follow-ups worth filing
    ```

    Follow-ups are *reported* in that comment for the developer to triage. Never
    file them as issues yourself.

## Code standards

Step 5's dispatch prompt MUST carry this section verbatim — the subagent never
reads this file.

**The code is the documentation.** Meaning lives in intention-revealing names,
functions small enough to do one thing, signatures and types that state the
contract, and control flow shallow enough to read top to bottom. Effort that
would go into explaining a confusing block goes into making the block
unconfusing. A comment is never a substitute for a clearer name or a smaller
function.

**A comment earns its place only by carrying what the code cannot:** why a
non-obvious approach beat the obvious one, a constraint imposed from outside (a
protocol quirk, an upstream bug, a measured performance trade-off), or a warning
about a consequence a reader would not predict. Public-API doc comments follow
whatever convention the repo already uses.

Everything else stays out: no narration of what the next line does, no
step-by-step running commentary, no change-name or ticket references, no
restating a task from the plan, no banner comments labelling sections that names
already label. The record of *what changed and why* lives in the commit and the
pull request — not in the source.

Judge the result by the code, not by its annotations. Heavily commented code a
reader still has to decode has failed this standard; uncommented code that reads
plainly has met it.

## Escalation and stop

Escalating is a legitimate outcome, not a failure — but it costs the developer
attention, so spend it only on ambiguity with no defensible default, or on a
blocker you genuinely cannot clear. Leave a durable, self-contained record: what
you were doing, what specifically is ambiguous or broken, what you already tried,
and the **numbered specific questions** you need answered.

In issue mode that record is a comment plus a label:

```bash
gh issue edit <n> --add-label "agent:needs-clarification" --remove-label "agent:working"
gh issue comment <n> --body "..."
```

Use `agent:blocked` instead of `agent:needs-clarification` when the intent is
clear but the gate will not pass, and paste the actual failure output. If you got
as far as working code, push the branch and open a **draft** pull request so the
work is not lost. Unassign yourself either way.

Without an issue there is nothing to label: report the same record in the session
and stop. A caller that dispatched this cycle — `arbor-auto-developer`, say —
owns the bookkeeping for a cycle that did not ship, and reads the outcome you
return.

In both cases, notify the developer out of band with `PushNotification` — a
comment alone will not reach them on a loop that runs unattended. Then stop. Do
not guess and merge.

## Labels this skill relies on (issue mode)

| Label                       | Meaning                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| `agent:working`             | A cycle owns this issue right now. Acts as the concurrency lock. |
| `agent:done`                | Shipped and merged by a cycle.                                   |
| `agent:blocked`             | Implementation exists but the gate will not pass. Needs a human. |
| `agent:needs-clarification` | Ambiguous intent. Questions are in the comments.                 |
| `p0` / `p1` / `p2`          | Selection priority, highest first.                               |

`templates/` in this skill directory ships the GitHub issue and pull request
templates that make those labels and the acceptance-criteria contract real in a
repo, along with the one-off commands that create the labels. A repo adopting
issue mode copies them into its `.github/`; see `templates/README.md`.

## Guardrails

- **Never integrate work that has not passed both gates.** A partial gate is a
  failing gate, and a green gate on the wrong feature is a failed cycle.
- **The plan writes no files.** It is session state threaded into the
  implementation — never a proposal, spec, or task artifact committed to the repo.
- The roadmap flip, the issue close-out, and any archival happen only because
  their step was reached — never as bookkeeping independent of the gate outcomes.
- A gate stage may only be treated as skipped when it itself reports an
  environment-blocked outcome — never as a shortcut, and never for a genuine
  failure against infrastructure that did come up. When step 6 reports one, that
  skipped stage MUST leave a visible trace (commit bullet, and PR/merge note if
  applicable) — never merge unverified changes silently.
- **Reject malformed model tokens.** An unknown phase key or model name stops the
  run at step 0, before any branch exists or any issue is claimed — never
  silently drop it or substitute a default.
- **Always dispatch each phase as a synchronous subagent** carrying its phase's
  model, and always pass the plan and the code standards into the implementation
  dispatch.
- **Never author or re-scope issues or roadmap items.** You claim them, build
  them, and close them; the developer writes them. Follow-up work is reported in
  a comment, never filed as new work by you.
- One change = one work ID = one branch = one work source. Keep them in sync, and
  never batch two issues or two roadmap items into one cycle.
