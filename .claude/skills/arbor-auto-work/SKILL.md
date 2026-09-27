---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work — take the intent, assign a work ID, branch, plan the slice into acceptance criteria and tasks, implement it, gate on the project's verification command, verify the diff against the intent, commit, push, and integrate. Use when starting or completing any non-trivial change. Each phase runs as a subagent under a per-phase model (defaults plan=opus, work=sonnet, gate=haiku), overridable with plan:/work:/gate: tokens, plus its own review: token for the intent gate, an optional roadmap: item reference this cycle closes out on commit, an optional issue: reference (a number, or issue:next to select one) making a GitHub issue the cycle's contract — claimed, verified against, and closed on merge — and an optional jira: reference (an issue key, or jira:next to select one from the project recorded in .arbor/config.json) doing the same for a Jira issue. Defaults to autonomous; pass --interaction to run with approval prompts, or --pr to run autonomously but open a pull request instead of merging. Pass --parallel (or --parallel=<n>, cap 1–8, default 4) to fan out agents inside each phase — codebase scouts, implementation waves in separate git worktrees, parallel gate fixes, and parallel intent reviewers — for a faster cycle at a higher token cost, with a scout: model token for the scouts (default haiku).
license: MIT
metadata:
  author: arbor
  version: "3.3"
---

# Arbor work cycle

The required process for all non-trivial work in a repo: work ID, branch, plan,
implement, gate, intent gate, commit, push, integrate. Two modes:

- **autonomous** (default): proceed through every step without prompts; merge to
  `main` at the end. Pass `--pr` to end by pushing and opening a pull request
  instead of merging — still no prompts.
- **interactive** (`--interaction`): ask for approval before implementing and
  before integrating; open a pull request at the end instead of merging.

Either mode can add `--parallel`, which fans agents out inside each phase to
cut wall-clock time without changing what the cycle ships. See
`## Parallel mode`.

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
`--models`), a `review:` model for the intent gate, `--parallel` or
`--parallel=<n>` with a `scout:` model for its scouts (see `## Parallel mode`),
a roadmap item reference
(`roadmap:docs/roadmaps/<slug>.md#R<n>`, the format `arbor-auto-roadmap` defines)
naming the roadmap item this cycle is building, an issue reference
(`issue:<n>`, or `issue:next` to select one) naming the GitHub issue this cycle
is building, and a Jira reference (`jira:<KEY-n>`, or `jira:next` to select one)
naming the Jira issue this cycle is building.

The roadmap and tracker references are all optional: omitting them runs the
cycle unchanged — no flip, no claim, no close-out, no error. `issue:` and
`jira:` are mutually exclusive — one cycle builds one tracker issue — and
passing both is a hard error at step 0.

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
| `scout:`  | codebase scouts (`--parallel` only)       | **haiku**  |

`review:` defaults to opus because the intent gate is the judgement call that
replaces human review. `scout:` defaults to haiku because scouts only locate
and summarize code; the plan model still does the planning. Without
`--parallel`, a `scout:` token is accepted and ignored.

**Syntax.** Bare tokens (primary) or a `--models` list — both parse identically:

```
<description> plan:opus work:sonnet
<description> --models plan:opus,work:sonnet
```

**Parsing.**

- A token matching `^(plan|work|gate|review|scout):(opus|sonnet|haiku|fable)$` — or a
  comma-separated list of them behind `--models` — is a model assignment and is
  removed from the input.
- `--parallel` or `--parallel=<n>` sets the concurrency cap (default 4). `<n>`
  must be an integer from 1 to 8; anything else is a hard error.
- After removing model tokens, the `--interaction`/`--pr`/`--parallel` flags,
  and any `roadmap:`/`issue:`/`jira:` token, whatever remains is the work description.
- An **unknown phase key or model name** (e.g. `wrok:sonnet`, `plan:opua`) is a
  hard error: **stop and report** it. Never silently ignore a mistyped override
  or fall back to a default in its place.
- Unspecified phases use their default tier from the table above.

Dispatch every phase **synchronously** (`run_in_background: false`) — each phase
depends on the previous one's output and file changes. Subagents share this
working directory, so the implementation phase sees the plan's context and the
gate sees the implementation's edits. Under `--parallel`, each phase still
completes before the next begins, but a phase may fan out concurrent agents as
`## Parallel mode` describes.

## Work sources

Four ways a cycle learns what to build. They differ only in where the intent
comes from and what is closed out at the end; steps 2–6 and 9 are identical in
all four.

| Source                | Intent contract is…                                            | Closed out by…                                 |
| --------------------- | -------------------------------------------------------------- | ---------------------------------------------- |
| `issue:<n>`           | the issue body and its comments, restated as a contract comment  | `Closes #<n>` plus the label swap in step 10   |
| `jira:<KEY-n>`        | the same, on the Jira issue (see `## Jira mode`)                 | a Done transition plus the label swap          |
| `roadmap:…#R<n>`      | the item's why-plus-acceptance-criteria text, verbatim            | the checkbox flip and commit bullets in step 8 |
| neither (description) | the description, made concrete by the plan written in step 4     | nothing beyond the commit                      |

Whichever applies, that source's acceptance criteria are what the intent gate at
step 7 checks the diff against. Passing a tracker reference (`issue:` or `jira:`)
together with `roadmap:` is allowed — an issue that builds a roadmap item — and
both close-outs then run.

**Issue mode** below means either tracker. The steps are written against
GitHub's `gh` commands; in Jira mode each of those operations is swapped for its
Jira equivalent from `## Jira mode`, and everything else — claim before branch,
intent contract before code, close out only after the merge — is unchanged.

## Steps

You MUST create a todo per step and complete them in order.

0. **Split off model, roadmap, and tracker tokens.** Set aside any
   `plan:`/`work:`/`gate:`/`review:`/`scout:` tokens (bare or behind
   `--models`), the `--interaction`/`--pr`/`--parallel` flags, any `roadmap:`
   token, and any `issue:` or `jira:` token.
   Reject an unknown phase key or model name, or a `--parallel=<n>` outside
   1–8, with a hard error — stop and report, before any branch is created or any
   issue is claimed. Fill unspecified phases with their defaults (plan=opus,
   work=sonnet, gate=haiku, review=opus, scout=haiku), hold the resolved
   concurrency cap when `--parallel` was passed, and hold
   the resolved model map for the dispatches below. What remains is the work
   description used everywhere below. Keeping all of them out now ensures none
   leaks into the work-ID slug in steps 2–3.

   **Preconditions.** Before touching anything: the working tree is clean
   (`git status --porcelain` is empty), you are on the default branch, and it is
   up to date (`git pull --ff-only`). In GitHub issue mode, `gh auth status`
   must also succeed; in Jira mode, the Jira access check from `## Jira mode`
   must. Any failure stops the run here.

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

   If a `jira:` token was supplied, resolve and claim it exactly as below, using
   the Jira lock query, eligibility query, and claim from `## Jira mode`.

   If an `issue:` token was supplied, resolve and **claim** the issue now, also
   before the branch exists. First check the lock — no other cycle may hold one:

   ```bash
   gh issue list --label "agent:working" --state open
   ```

   If that returns an issue, another cycle owns it. Either resume that issue (its
   branch exists and no other process is live) or stop. Never run two cycles at
   once. Then resolve the reference:

   - `issue:<n>` — use that issue. It must be open, must not be a pull request,
     and must not carry `agent:blocked`, `agent:needs-clarification`, or
     `epic`. Each of those is a hard error that stops the run.
   - `issue:next` — select the first eligible issue: open, not a pull request,
     not labelled `agent:blocked`, `agent:needs-clarification`, or `epic`,
     unassigned, ordered by priority label `p0` > `p1` > `p2` > unlabelled,
     then oldest `createdAt`.

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
   counter, so `issue:42` does not make the work ID `DEV-42-<slug>`, and
   `jira:SHOP-42` does not make it `SHOP-42-<slug>`. A Jira key has the same
   shape as a work ID, so it never goes in a commit subject or a branch name —
   only in the commit body (step 8) — or the scan above would count it.

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

   With `--parallel`, scouts run first and the plan also carries a task graph in
   waves — see `### Plan` under `## Parallel mode`.

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

   Where the gate enforces a threshold — a coverage percentage, a lint rule, a
   type-strictness setting, a size budget — it is met by changing the code, never
   by weakening the threshold. A branch that is hard to cover gets **lifted into a
   tested module**; it is never added to a coverage exclusion list, and no rule is
   suppressed inline, no escape hatch reached for (a non-null assertion, an
   `any`, a disabled check), to make a number go green. Moving the goalposts is a
   failed cycle wearing a green gate.

   Stay inside the slice's scope. Unrelated problems you notice are follow-up
   work to report at step 10, not extra commits on this branch. If the phase hits
   a genuine blocker — an ambiguous task, an error it cannot clear — it reports
   that back instead of a clean completion; treat that as a real problem and stop
   rather than continuing to the gate.

   With `--parallel`, the plan's waves are implemented by concurrent agents in
   separate worktrees — see `### Implement` under `## Parallel mode`. A plan
   with a single task runs this step exactly as written.

6. **Run the gate (gate model).** If the project defines a verification command —
   an `npm run gate` / test / lint / build script, or a gate documented in the
   repo — dispatch a subagent with `model` = the **gate** model to run the
   **full** gate, not a convenient subset, and report its outcome faithfully. It
   MUST pass end-to-end; do not proceed otherwise. A genuine failure is a real
   defect to surface and fix, never something to work around or paper over. If
   the repo defines no such command, note that and continue.

   A full gate can outrun a foreground command timeout — a cold container build, a
   large test matrix, an e2e suite. Run it in the background and wait on
   completion rather than polling blindly or trimming stages to fit. Where the
   repo has no CI, this local run is the only verification the change will ever
   get; treat it accordingly. Keep the passing run's tail — it is the gate
   evidence step 10 puts in the pull request or the merge note.

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
     fix it, then re-run **the whole gate**, not just the stage that failed. An
     earlier stage can regress on the fix, and only a full green run is evidence.

   A failure that looks incidental rather than caused by the change — a registry
   hiccup mid-build, a container that never became healthy, a process killed under
   host memory pressure — may be re-run **once** before it is treated as real. A
   test that actually executed and failed its assertion is real on the first run;
   never re-roll one of those hoping for a different answer.

   A genuine gate failure stops the cycle here; do not continue to the intent
   gate or the commit on a red gate.

   With `--parallel`, the gate run is unchanged, but fixes for failures in
   separate tasks run concurrently — see `### Gates` under `## Parallel mode`.

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

   With `--parallel`, the criteria are split across concurrent reviewers plus
   one scope reviewer — see `### Gates` under `## Parallel mode`.

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

   With `--parallel`, first fold the wave checkpoint commits back into the
   working changes with `git reset --soft <branch-point>` (the commit the branch
   was created from), so the cycle still lands as a single commit.

   Commit with a subject `{ticket} {short description}` (uppercase work ID,
   e.g. `DEV-4 add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented. If step 6
   reported an environment-blocked stage — which still reaches the flip and
   any archival above — add a bullet surfacing it, e.g. `- E2E skipped:
   environment-blocked (<reason>); not independently verified.` If a
   `roadmap:` reference was supplied, add `- Roadmap: <slug> R<n> complete`
   (`<slug>` is the roadmap filename without its `.md` extension); if the flip
   also archived the file, additionally add `- Roadmap <slug> complete;
   archived`. If an `issue:` reference was supplied **and this cycle merges
   straight to the default branch**, add a `Closes #<n>` line so that merge
   closes the issue; when the work lands through a pull request instead —
   `--pr`, interactive, or an autonomous self-merge in a repo that integrates
   through pull requests — `Closes #<n>` belongs in the PR body at step 10, not
   here. If a `jira:` reference was supplied, add a `Jira: <KEY-n>` line to the
   body — never the subject — in every integration mode; Jira closes on the
   explicit transition at step 10, not on a commit keyword. All of these
   bullets are independent and may appear together in one commit body.

9. **Push** the branch.

10. **Integrate and close out.** Autonomous: merge to `main` — unless `--pr` was
    passed, in which case push and open a pull request instead of merging.
    Interactive: ask for approval, then open a pull request.

    Where the repo integrates through pull requests, an autonomous cycle still
    goes through one — open it, then merge it yourself:

    ```bash
    gh pr merge <pr> --merge --delete-branch
    ```

    That is a self-merge, not a review request: no human approves it, and the
    pull request exists to carry the record. `Closes #<n>` then lives in the PR
    body rather than the commit, and closes the issue when the merge lands.

    Where the repo ships a pull request template, fill it; otherwise the body
    carries `Closes #<n>` in GitHub issue mode (`Jira: <KEY-n>` in Jira mode), the step 7 verdict table mapping each
    acceptance criterion to the code that satisfies it, the gate evidence from
    step 6 (including any environment-blocked stage and its reason), and the
    assumptions from the intent contract.

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

    In Jira mode the close-out is the same sequence through `## Jira mode`: pull
    `main`, transition the issue to done, swap `agent-working` for `agent-done`,
    and post the closing comment. Nothing closes a Jira issue implicitly, so the
    transition is always explicit.

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
clear but the gate will not pass, and paste the actual failure output. In Jira
mode the record is the same comment plus the hyphenated label
(`agent-needs-clarification` or `agent-blocked`), with `agent-working` removed. If you got
as far as working code, push the branch and open a **draft** pull request so the
work is not lost. Unassign yourself either way.

Without an issue there is nothing to label: report the same record in the session
and stop. A caller that dispatched this cycle — `arbor-auto-developer`, say —
owns the bookkeeping for a cycle that did not ship, and reads the outcome you
return.

In both cases, notify the developer out of band with `PushNotification` — a
comment alone will not reach them on a loop that runs unattended. Then stop. Do
not guess and merge.

## Jira mode

A `jira:` reference makes a Jira issue the cycle's contract. The project comes
from `.arbor/config.json` (`roadmap.jira.project`, the key `arbor-auto-roadmap`
and `arbor-project-scaffold` record); a `jira:<KEY-n>` whose project differs
from it is still honoured, since the key names its own project. `jira:next`
with no project recorded is a hard error at step 0.

Use a connected Atlassian/Jira MCP server's tools when one is available,
otherwise the `jira` CLI. **Access check:** the MCP server answers a lookup of
the project, or `jira me` succeeds and `jira project list` includes it.

| Operation               | Jira equivalent (CLI shown; MCP tools map one-to-one)                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| Lock check              | `jira issue list -q 'project = <KEY> AND labels = agent-working AND statusCategory != Done' --plain`    |
| Eligible issues         | the query below                                                                                         |
| Read issue and comments | `jira issue view <KEY-n> --comments 100 --plain`                                                        |
| Claim                   | `jira issue edit <KEY-n> -l agent-working --no-input`, `jira issue assign <KEY-n> "$(jira me)"`, then `jira issue move <KEY-n> "<startTransition>"` and confirm `statusCategory = In Progress` |
| Comment                 | `jira issue comment add <KEY-n> "<body>"`                                                               |
| Swap labels             | `jira issue edit <KEY-n> -l -agent-working -l agent-done --no-input` (a leading `-` removes a label)    |
| Unassign                | `jira issue assign <KEY-n> x`                                                                           |
| Close                   | `jira issue move <KEY-n> "<doneTransition>"`, then confirm `statusCategory = Done`                      |

Eligibility — open, not an Epic, unassigned, not locked, blocked, or awaiting
clarification — in selection order, Jira's Priority field highest first, then
oldest:

```
project = <KEY> AND statusCategory != Done AND issuetype != Epic
  AND assignee IS EMPTY
  AND (labels IS EMPTY OR labels NOT IN (agent-working, agent-blocked, agent-needs-clarification))
ORDER BY priority DESC, created ASC
```

The `labels IS EMPTY` arm is load-bearing: `NOT IN` alone silently drops every
issue that has no labels at all.

`<startTransition>` is `roadmap.jira.startTransition` from the config, default
`In Progress`. It is part of the claim: a claimed issue must show as in
progress on the board, not sit in To Do with a label on it. Skip the move only
when the issue's `statusCategory` is already In Progress. `<doneTransition>` is
`roadmap.jira.doneTransition` from the config, default `Done`. If the workflow
has no such transition from the issue's current status — either one — escalate
as blocked rather than guessing another one. The issue's description (and its acceptance
criteria, however they are formatted there) plus every comment is the contract,
exactly as with a GitHub issue body.

## Parallel mode

`--parallel` cuts the wall-clock time of one cycle by fanning agents out inside
steps 4–7 wherever the work splits. It changes nothing the cycle ships: both
gates still pass on the merged result, and the cycle is still one work ID, one
branch, one work source, and one commit. Steps 0–3 and 8–10 run as written. It
composes with every other flag and reference.

It trades tokens for time — scouts, parallel reviewers, and per-worktree
dependency installs all cost more than the sequential cycle.

**Mechanics.** The session running this skill is the **orchestrator**: it
dispatches, validates, merges, and combines results, and never implements.
Agents that run concurrently are dispatched **in a single message**, and all of
them are awaited before moving on. The concurrency cap bounds every fan-out; a
larger fan-out runs in batches of at most the cap.

### Plan

**Scouts** (`scout:` model, concurrent). From the step 1 contract and a cheap
map of the repo — `git ls-files` grouped by top-level directory, plus
`CLAUDE.md` and `docs/CONVENTIONS.md` if present — pick up to *cap* areas worth
reading: the packages or directories the contract touches, and where their
tests live. A narrow slice or a small repo gets one scout. Each scout reads only
its area, **writes nothing**, and returns at most ~400 words:

- the relevant files, by path;
- key types and signatures, and existing patterns to reuse;
- where the area's tests live, and the command that runs only them;
- shared plumbing it saw — registries, barrel or index files, routing tables,
  config, `package.json`, lockfiles.

**Planner** (`plan:` model). Dispatch step 4 as written, adding every scout
summary to its inputs; it may still read files to fill gaps. Besides the usual
plan it returns a **task graph**, still as session state:

```
T1  <what to do>
    owns:     src/cart/cart.ts, src/cart/cart.test.ts
    serves:   AC1, AC3
    test:     npm test -- src/cart
    after:    —
T2  ...
    after:    T1
Waves: W1 = {T1, T3}  W2 = {T2}  W3 = {T4 (integration)}
```

**Validation.** The orchestrator checks the graph:

1. **Disjoint ownership** — no file is owned by two tasks in the same wave.
2. **Backward dependencies** — `after:` only names tasks in earlier waves.
3. **Serialized plumbing** — edits to shared wiring (registries, index files,
   routes) belong to one **integration task** in the final wave; dependency
   installs and lockfile changes belong to one task in **W1**.
4. **Coverage** — every acceptance criterion is served by at least one task.

On a violation, send the violations back to the planner **once**. If the
corrected graph still fails, fall back to sequential step 5 with the plan as an
ordinary task list. Never guess at a partition. A graph of one wave holding one
task also runs sequential step 5; log `parallel: no independent tasks`.

### Implement

If `--interaction`, show the plan with its waves and get approval before the
first wave. Then, per wave:

1. **Dispatch.** One agent per task, each with `isolation: "worktree"` and
   `model` = the `work:` model. Each worktree branches from the feature branch's
   current HEAD, so it holds every earlier wave. Each agent receives the full
   plan, its own task ID and owned files, and the **Code standards** section
   verbatim, plus these rules:
   - edit only owned files — if the task cannot be done without touching
     another file, stop and report a blocker instead;
   - run the task's `test:` command until it passes; never run the full gate;
   - commit on the worktree branch as `wip <task-id>`, then report the branch,
     the commit SHA, the changed files, and the tail of the test output.
2. **Dependencies.** A fresh worktree has no installed dependencies. If the
   main checkout has a dependency directory (`node_modules`, `.venv`, `vendor`,
   …) and the wave changes no lockfile, the agent symlinks it from the main
   checkout; otherwise it runs the repo's install command in its worktree. The
   W1 dependency task always installs for real.
3. **Ownership check.** For each task, run
   `git diff --name-only <wave-base>..<sha>`. A file outside the task's
   ownership rejects it: re-dispatch it **once**, naming the offending files. A
   second stray is a blocker.
4. **Merge.** Merge each task branch into the feature branch in task order.
   Disjoint ownership rules out a textual conflict; if one occurs anyway, it is
   a blocker. Then run the union of the wave's `test:` commands on the merged
   tree, one after another, to catch tasks that pass alone but break together.
   A failure there gets one fix agent on the merged tree in the main checkout,
   then the wave's tests run again.
5. **Checkpoint.** Commit the merged wave on the feature branch as a checkpoint;
   the next wave branches from it. Remove each worktree once its branch has
   merged.

If any agent in a wave reports a blocker, let the rest of the wave finish,
merge **nothing** from that wave, and escalate per `## Escalation and stop` —
push the branch holding the completed waves, open a draft pull request, label,
and notify.

### Gates

**Verification gate.** Step 6's run is unchanged: one `gate:` agent runs the
**full** command on the merged branch. Never shard or subset the gate; making
the command itself faster is the project's concern. On failure, the gate agent
reports each failure with the files it implicates, and the orchestrator maps
them to tasks by ownership:

- failures in distinct tasks get **one fix agent per task, concurrently**,
  under the `### Implement` rules — worktree, owned files only, the task's
  `test:`, commit, ownership check, merge;
- failures that map to no single task (lint config, cross-cutting) go to
  **one** fix agent in the main checkout;
- then the **full** gate runs again.

**Intent gate.** Every reviewer is a fresh `review:` agent that wrote no code;
dispatch them all in one message:

- **Criteria reviewers** — split the acceptance criteria into up to *cap*
  groups. Each reviewer gets the full contract, the full branch diff, and its
  own criteria, and returns step 7's per-criterion verdict, defaulting to
  `not satisfied` when it cannot find the evidence.
- **Scope reviewer** — gets the contract, every criterion, and the diff, and
  reports only changes no criterion asked for.

Combine the results into the single verdict table step 10 uses. For an unmet
criterion, re-dispatch the tasks that `serves:` it as a **fix wave** carrying
the reviewers' notes, then re-run the full gate and the **entire** intent gate
over every criterion — a fix can regress one that passed.

## Labels this skill relies on (issue mode)

| Label                       | Meaning                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| `agent:working`             | A cycle owns this issue right now. Acts as the concurrency lock. |
| `agent:done`                | Shipped and merged by a cycle.                                   |
| `agent:blocked`             | Implementation exists but the gate will not pass. Needs a human. |
| `agent:needs-clarification` | Ambiguous intent. Questions are in the comments.                 |
| `epic`                      | Umbrella/tracking issue. Scope reference, never built directly.  |
| `p0` / `p1` / `p2`          | Selection priority, highest first.                               |

In Jira the same labels are spelled with a hyphen (`agent-working`,
`agent-done`, `agent-blocked`, `agent-needs-clarification`), `epic` is the Epic
issue type rather than a label, and priority is Jira's own Priority field.

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
- **Each phase completes before the next begins.** Without `--parallel`, a
  phase is one synchronous subagent; with it, a phase may fan out concurrent
  agents, dispatched in one message and all awaited before the next phase.
- **Always dispatch each phase as a subagent** carrying its phase's
  model, and always pass the plan and the code standards into the implementation
  dispatch.
- **Never author or re-scope issues or roadmap items.** You claim them, build
  them, and close them; the developer writes them. Follow-up work is reported in
  a comment, never filed as new work by you.
- **Describe the project on its own terms.** Never position or explain it by
  naming or comparing against another software product — not in code, docs,
  commits, issues, or pull requests. Naming a tool the project actually depends
  on or is migrating from is ordinary and fine; framing the project as an
  alternative to something else is not.
- One change = one work ID = one branch = one work source. Keep them in sync, and
  never batch two issues or two roadmap items into one cycle, or pass both an
  `issue:` and a `jira:` reference.
