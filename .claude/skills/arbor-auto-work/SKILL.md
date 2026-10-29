---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work or a ticket — take the intent (a description, a ticket key or link, a ticket: reference, or a roadmap: item), use the ticket key as the work ID or assign one, branch (or create a multi-repo workspace when run from a projects root), plan the slice into acceptance criteria and tasks, implement it, verify it with the full unit, integration and automation suites plus in-browser checks, review the diff against the intent, publish a templated implementation report on localhost, then commit, push, and integrate. Use when starting or completing any non-trivial change, or when given a ticket to implement. Works with any ticket system, code host and version control system: their commands come from provider mappings kept on the local machine, built from the session's own tools when missing. Each phase runs as a subagent under a per-phase model (defaults plan=opus, work=sonnet, gate=haiku), overridable with plan:/work:/gate: tokens, plus its own review: token for the intent gate, an optional roadmap: item reference this cycle closes out on commit, and an optional ticket reference (ticket:<key|number|url>, or ticket:next to select one) making a ticket the cycle's contract — claimed, verified against, and closed on merge. A project profile (.arbor/auto-work.md, nearest ancestor) adds providers, repo maps, local-stack and test-data recipes, and house rules. Defaults to fully autonomous; pass --manual to stop before committing so the user reviews the report and commits and pushes from its buttons, --interaction to run with approval prompts, or --pr to open a change request instead of merging. Pass --parallel (or --parallel=<n>, cap 1–8, default 4) to fan out agents inside each phase for a faster cycle at a higher token cost, with a scout: model token for the scouts (default haiku).
license: MIT
metadata:
  author: arbor
  version: "5.0"
---

# Arbor work cycle

The required process for all non-trivial work: work ID, branch, plan,
implement, verify, review, report, commit, push, integrate. Modes:

- **autonomous** (default): proceed through every step without prompts; merge
  to the base branch at the end. Pass `--pr` to end by pushing and opening a
  change request instead of merging — still no prompts.
- **manual** (`--manual`): run every step through the report, then **stop
  before committing**. The agent never stages, commits or pushes; the user
  reviews the report page and commits and pushes with its **Commit & push**
  button. The ticket is only read, never claimed, commented on or moved.
- **interactive** (`--interaction`): ask for approval before implementing and
  before integrating; open a change request at the end instead of merging.

`--manual` is mutually exclusive with `--pr`; passing both is a hard error at
step 0. Any mode can add `--parallel`, which fans agents out inside each phase
to cut wall-clock time without changing what the cycle ships. See
`## Parallel mode`.

"Change request" means whatever the code host calls a proposed merge. Every
concrete command for the ticket system, the code host and the version control
system comes from a provider mapping (`## Providers`); this skill names only the
operations.

The plan from step 4 is threaded into the implementation and saved, outside
the repos, as the report's spec. The code is the deliverable; the record of
what changed and why lives in the report, the commit and the change request. A
repo that uses the OpenSpec lifecycle (its profile or its own `CLAUDE.md` says
so) goes through propose, apply and archive in step 5; every other repo is
implemented directly, with no spec artifacts committed.

## The two gates

Everything here serves two gates. Both must pass before an integration.

1. **The verification gate** — the project's verification command and every
   test suite of every changed repo pass in full, and the behavior is checked
   end to end, at step 6. This proves the code _works_.
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
hand back the whole decision. `--manual` changes only where the cycle ends, not
how much it asks along the way.

## Inputs

A short description of the slice of work, and optionally:

- a **work-ID prefix** — an uppercase word for the kind of work (e.g. `FEAT`,
  `OPS`), used only when no ticket supplies the ID (step 2);
- a **mode** — `--manual`, `--interaction` or `--pr`;
- **model tokens** — `plan:`/`work:`/`gate:`, bare or behind `--models`, a
  `review:` model for the intent gate, and `--parallel` or `--parallel=<n>`
  with a `scout:` model for its scouts (see `## Parallel mode`);
- a **roadmap item reference** (`roadmap:docs/roadmaps/<slug>.md#R<n>`, the
  format `arbor-auto-roadmap` defines) naming the roadmap item this cycle is
  building;
- a **ticket reference** naming the ticket this cycle is building:
  `ticket:<ref>`, where `<ref>` is a ticket key (`PROJ-123`), a number, or a
  link, or `ticket:next` to select one. A bare ticket key or ticket link given
  as its own token is the same as `ticket:<ref>`.

The roadmap and ticket references are both optional: omitting them runs the
cycle unchanged — no flip, no claim, no close-out, no error. One cycle builds
one ticket, so passing two ticket references is a hard error at step 0.

## Model selection

Every phase runs as a subagent dispatched with an explicit `model`. The four
accepted model names are exactly the Agent tool's `model` values — `opus`,
`sonnet`, `haiku`, `fable` — passed straight through; the skill never resolves
concrete model ids itself. Each phase has a default tier, used when the caller
does not override it:

| Knob      | Phase                                     | Default    |
| --------- | ----------------------------------------- | ---------- |
| `plan:`   | plan the slice (step 4)                   | **opus**   |
| `work:`   | implement the slice and fix findings      | **sonnet** |
| `gate:`   | run the verification suites (step 6)      | **haiku**  |
| `review:` | the intent gate (step 7)                  | **opus**   |
| `scout:`  | codebase scouts (`--parallel` only)       | **haiku**  |

`review:` defaults to opus because the intent gate is the judgement call that
replaces human review. `scout:` defaults to haiku because scouts only locate
and summarize code; the plan model still does the planning. Without
`--parallel`, a `scout:` token is accepted and ignored. In-browser verification
(step 6) and every fix run under the `work:` model; if a fix needs a design
decision, correct the plan with the `plan:` model rather than upgrading the
implementer.

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
- After removing model tokens, the `--manual`/`--interaction`/`--pr`/`--parallel`
  flags, any `roadmap:` token, and any ticket reference, whatever remains is the
  work description. With a ticket and no description, the ticket's summary is
  the description.
- An **unknown phase key or model name** (e.g. `wrok:sonnet`, `plan:opua`) is a
  hard error: **stop and report** it. Never silently ignore a mistyped override
  or fall back to a default in its place.
- Unspecified phases use their default tier from the table above.

Dispatch every phase **synchronously** (`run_in_background: false`) — each phase
depends on the previous one's output and file changes. Subagents share this
working directory, so the implementation phase sees the plan's context and the
gate sees the implementation's edits. Under `--parallel`, each phase still
completes before the next begins, but a phase may fan out concurrent agents as
`## Parallel mode` describes. Long test runs inside a phase run in the
background and are waited on, never polled blindly. Every phase that runs VCS,
code-host or ticket operations receives the relevant provider mappings.

## Work sources

Three ways a cycle learns what to build. They differ only in where the intent
comes from and what is closed out at the end; steps 2–6 and 9 are identical in
all three.

| Source                | Intent contract is…                                                   | Closed out by…                                     |
| --------------------- | --------------------------------------------------------------------- | -------------------------------------------------- |
| a ticket              | the ticket's description and comments, restated as a contract comment | the ticket's close plus the label swap in step 10  |
| `roadmap:…#R<n>`      | the item's why-plus-acceptance-criteria text, verbatim                 | the checkbox flip and commit bullets in step 8     |
| neither (description) | the description, made concrete by the plan written in step 4          | nothing beyond the commit                          |

Whichever applies, that source's acceptance criteria are what the intent gate at
step 7 checks the diff against. Passing a ticket together with `roadmap:` is
allowed — a ticket that builds a roadmap item — and both close-outs then run.
Under `--manual` no ticket close-out runs: the user integrates, and the ticket
is theirs to move.

**Ticket mode** below means a cycle with a ticket reference.

## Layout and project profile

**Repo mode** (the usual case): the current directory is inside a version-
controlled repository. The cycle branches that repo and works in place. The
**work dir** — where the report data, spec and evidence live — is
`~/.arbor-reports/<ID>/work/`, outside the repo.

**Workspace mode**: the current directory is not inside a repository, and it or
an ancestor holds `repositories.json` (a projects root set up by
`arbor-workspace-init`); or the current directory is inside an existing
workspace (an ancestor holds `.workspace.json`). The plan picks the repos, and
the cycle works in a workspace from `arbor-workspace-create` — one clone per
repo, all on one branch. The work dir is the workspace root. Never work in the
projects root's long-lived `development/` clones.

**Project profile.** The nearest `.arbor/auto-work.md` walking up from the
current directory, if any, is the project profile: providers, repo map,
local-stack and test-data recipes, test commands, report settings and house
rules. Read `references/profile.md` for how it applies; `arbor-auto-setup`
builds one by interviewing the user. Its hard rules are hard
rules of this cycle, and it is passed to every phase that needs it; it never
loosens a gate.

## Providers

Three providers serve a cycle. The skill names their **operations**; each
provider's **mapping** gives the exact commands.

| Provider | Identified by | Operations |
| --- | --- | --- |
| **VCS** | what the repository is under version control with | clean check · current branch · default branch and update it · create branch · diff against the base (committed plus uncommitted) · ID scan (every commit subject and branch name) · list tracked files · stage all and commit · fold commits back to a point, keeping the changes · move a tracked file · push · merge into the base · rebase onto the base · isolated working copy for a parallel agent · files changed between two points |
| **Code host** | the repository's remote | access check · open a change request (ready or draft) · self-merge it, deleting the branch · find the repo's change-request template · closing keyword, if the host closes tickets from one |
| **Test management** (optional) | the project profile | the skill to invoke · an API helper · the test-key format in test titles · which files are automated specs (`references/report.md`) |
| **Ticket system** | a ticket link names its own; otherwise the profile, else `.arbor/config.json`'s `roadmap.destination` (as `arbor-auto-roadmap` and `arbor-project-scaffold` write it), with its settings — project key, start and done transitions — under `roadmap.<destination>` | access check · lock check · select · read · claim · comment · swap labels · unassign · close |

**Where mappings live.** On the machine running the cycle, never in this skill:
the project profile's provider sections first, else
`~/.claude/arbor/providers/<vcs|host|tickets|tests>/<name>.md`. A mapping names its
tools — a connected MCP server's, or a CLI — and gives the exact call per
operation, plus whatever the provider needs: label spellings, the selection
query, how to find project or cloud identifiers, the closing keyword. A VCS
mapping also has a machine-readable twin, `<name>.json`, holding the commands
the report scripts run; its contract is the docstring of `report/vcs.py`, and
the report names it in its `vcs` field.

**Building a missing mapping.** At step 0, for each provider the cycle needs
and has no mapping for: identify it (the repository's metadata, its remote, the
ticket reference or config), look at the tools this session has for it — MCP
server tools first, otherwise a CLI's help — and pick the call for each
operation. Prove the mapping with read-only operations (the access check, a
status or a ticket read) before anything writes through it. Save it to
`~/.claude/arbor/providers/<kind>/<name>.md` so later runs on this machine
reuse it, and note in the report's `setup` that it was created. An operation
with no workable call is a blocker to escalate, never a step to skip.

### Ticket conventions

The ticket operations, whatever the system:

| Operation    | What it does                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------------- |
| Access check | confirm the tools can reach the project                                                        |
| Lock check   | list open tickets carrying the working label                                                   |
| Select       | list eligible tickets (open, not an epic or change request, unassigned, not working, blocked or needs-clarification), highest priority first, then oldest |
| Read         | the ticket, every comment, and what it links to                                                |
| Claim        | add the working label, assign yourself, move to in progress where there is a workflow          |
| Comment      | post a comment                                                                                 |
| Swap labels  | remove one label, add another                                                                  |
| Unassign     | clear the assignee                                                                             |
| Close        | close the ticket, or move it to done, and confirm it                                           |

Four labels carry a cycle's state, spelled as the mapping says:

| Label                | Meaning                                                           |
| -------------------- | ----------------------------------------------------------------- |
| working              | A cycle owns this ticket right now. Acts as the concurrency lock. |
| done                 | Shipped and merged by a cycle.                                    |
| blocked              | Implementation exists but the gate will not pass. Needs a human.  |
| needs-clarification  | Ambiguous intent. Questions are in the comments.                  |

An epic is an umbrella ticket — a scope reference, never built directly.
Priority is the system's own priority field, or `p0` > `p1` > `p2` > unlabelled
labels where it has none. A selection filter that excludes labels must still
match tickets with no labels at all: many query languages silently drop
unlabelled tickets from a "label not in" filter.

Where the system moves tickets through a workflow, the claim moves the ticket
with the start transition (`roadmap.<destination>.startTransition`, default
`In Progress`) unless it is already in progress, and the close uses the done
transition (`roadmap.<destination>.doneTransition`, default `Done`), each
confirmed afterwards. A claimed ticket must show as in progress, not sit in a
backlog column with a label on it. If the workflow has no such transition from
the ticket's current status, escalate as blocked rather than guessing another.
Where nothing closes a ticket implicitly, the close is always explicit.

When a system numbers tickets without a key, the cycle assigns its own work ID
(step 2).

## Steps

You MUST create a todo per step and complete them in order.

0. **Split off model, mode, roadmap, and ticket tokens.** Set aside any
   `plan:`/`work:`/`gate:`/`review:`/`scout:` tokens (bare or behind
   `--models`), the `--manual`/`--interaction`/`--pr`/`--parallel` flags, any
   `roadmap:` token, and any ticket reference (`ticket:`, a bare ticket key, or
   a ticket link).
   Reject an unknown phase key or model name, a `--parallel=<n>` outside
   1–8, two ticket references, or `--manual` together with `--pr`, with a hard
   error — stop and report, before any branch is created or any ticket is
   claimed. Fill unspecified phases with their defaults (plan=opus,
   work=sonnet, gate=haiku, review=opus, scout=haiku), hold the resolved
   concurrency cap when `--parallel` was passed, and hold the resolved model
   map for the dispatches below. What remains is the work description used
   everywhere below. Keeping all of them out now ensures none leaks into the
   work-ID slug in steps 2–3.

   **Layout, profile, and providers.** Decide repo mode or workspace
   mode (`## Layout and project profile`), and read the project profile if
   there is one. Identify the VCS and code host, and the ticket system in
   ticket mode, and load — or build and save — each one's mapping
   (`## Providers`). `ticket:next` with no ticket system identified is a hard
   error. If the profile names a test-management system, load its mapping
   too, and note whether the skill it names is in this session's skill list:
   only then does the report enable publishing to it (`references/report.md`).

   **Preconditions.** Before touching anything, in repo mode: the working copy
   is clean, you are on the default branch, and it is up to date. In workspace
   mode: the projects root and its `repositories.json` are found. The code
   host's access check must pass, and in ticket mode the ticket system's. Any
   failure stops the run here.

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

   In ticket mode, resolve and **claim** the ticket now, also before the branch
   exists. Under `--manual`, resolve and read it but skip the lock check and
   the claim. First **check the lock**: no other cycle may hold one. If a
   ticket carries the working label, another cycle owns it. Either resume that
   ticket (its branch exists and no other process is live) or stop. Never run
   two cycles at once. Then resolve the reference:

   - a specific ticket — use it. It must be open, must not be a change request,
     and must not carry the blocked or needs-clarification label or be an epic.
     Each of those is a hard error that stops the run.
   - `next` — **select** the first eligible ticket (`### Ticket conventions`).
     If nothing is eligible, say so and stop. Do not invent work, and never
     author a ticket to give yourself something to do — ticket content is the
     developer's to write.

   **Claim** it before any other action, so a concurrent run cannot pick the
   same one.

1. **Determine the slice, and state the intent contract.** Restate the smallest
   shippable unit of work. If it's too big for one change, stop and split it.

   In ticket mode, **read** the ticket in full, **including every comment**,
   and everything it links to: linked tickets, attachments, mockups, and
   linked documents or wiki pages. If the ticket system's tools are
   unavailable or fail, open the ticket in Chrome (load the `claude-in-chrome`
   skill first) and read the page. Extract the summary, description,
   acceptance criteria, repro steps, affected areas, and the kind of work
   (a bug → `bugfix`, a story, task or feature → `feature`, a production
   emergency → `hotfix`). Then answer three questions: what changes, and for
   whom; what the observable acceptance criteria are (each checkable — an
   input and an output, a visible behaviour, an error case; "works well" is not
   a criterion); which packages or repos it touches, and whether any
   dependency edge changes (a new edge that creates a cycle is a design error
   and needs justifying up front). If a question is unanswerable by any
   defensible assumption, escalate and stop.

   Otherwise post the intent contract as a ticket **comment before writing
   code** (under `--manual`, keep it in the session and the report instead).
   It states, in this order: what you are building; the numbered acceptance
   criteria you will verify against; every assumption you made and why;
   anything explicitly out of scope for this cycle. This comment is what the
   intent gate checks against at step 7, and it gives the developer a window
   to correct course asynchronously without blocking the loop.

   In roadmap mode the item's own text is the contract — it is already phrased as
   why-plus-acceptance-criteria — so restate it in the session rather than
   writing it anywhere. Never edit the roadmap to record it.

2. **Assign the work ID.** When the ticket has a key (`PROJ-123`), **its key is
   the work ID**; no new ID is created. Otherwise — no ticket, or a system
   that numbers tickets without a key — assign one: the prefix is the one
   passed in, else the profile's, else the uppercase prefix the repo's history
   already uses most, else `WORK`; the number is one more than the highest
   existing `<PREFIX>-<n>` across the repo's commit subjects and branch names
   (the VCS's ID scan).

   A ticket number is a reference the cycle carries, never the work-ID
   counter, so ticket `42` does not make the work ID `<PREFIX>-42`. The slug is
   a lowercase kebab-case summary of the work (e.g. `add-cart`).

3. **Create the branch or workspace.** The branch is
   `feature|bugfix|hotfix/<ID>-<slug>` (feature for features, bugfix for fixes,
   hotfix for hotfixes), e.g. `feature/PROJ-4-add-cart`.

   In repo mode, create it now. In workspace mode, this step runs right after
   step 4, because the plan chooses the repos: invoke `arbor-workspace-create`
   with the branch type, the work ID, the slug's words, and the plan's repo
   list, all supplied up front so it does not re-ask. If a workspace for the
   work ID already exists, reuse it (`arbor-workspace-add` for missing repos,
   `arbor-workspace-import` for an existing branch) rather than creating a
   duplicate. All work happens in the workspace clones.

   Then start `<work dir>/report.json` (`references/report.md`) and keep it
   current from here on. If an IDE's MCP tools are available, open each changed
   repo in the IDE and check its run configurations; if the IDE cannot open
   it, fall back to shells and say so in the report.

4. **Plan the slice (plan model).** Dispatch a subagent with `model` = the
   **plan** model. Give it the work description, the work source's contract from
   step 1, the project profile (repo map, conventions, environment), and the
   repo's conventions if documented (`CLAUDE.md`, `AGENTS.md`,
   `docs/CONVENTIONS.md`). Ask it to read enough of the codebase to plan against
   what is actually there, then return, **as text in the session**, a plan with
   no judgment calls left:

   - in workspace mode, **which repos to change** and which to leave alone, and
     why — following the call chain from UI to gateway to the API that owns the
     behavior, and changing the owning repo rather than working around it;
     schema and data changes go where the profile says, with the ordering
     between repos stated;
   - the numbered **acceptance criteria** the finished work must satisfy, each
     one observable and checkable;
   - a concrete **task list** — the ordered changes to make, named by file,
     signature or module, small enough that each is individually verifiable;
   - the **tests** to add: unit and integration tests, and, where a changed repo
     has an automation suite, the automation test (`references/verification.md`);
   - how to verify locally, and which local services that needs;
   - the **edge cases and error paths** that matter, and any design decision it
     had to make, with the reason.

   **It writes no files.** The orchestrator saves the returned plan to
   `<work dir>/spec.md` for the report — never into a repo. Where the work
   source's acceptance criteria and the plan diverge, the work source wins. If
   the repo choice is still ambiguous with no defensible default, escalate.

   Hold the returned plan; every later step refers back to it.

   With `--parallel`, scouts run first and the plan also carries a task graph in
   waves — see `### Plan` under `## Parallel mode`.

5. **Implement (work model).** If `--interaction`, summarize the plan and ask for
   approval before dispatching. Then dispatch a subagent with `model` = the
   **work** model — one per repo in workspace mode, concurrently when they are
   independent — carrying the full plan from step 4 verbatim, the profile's
   rules for that repo, and the **Code standards** section below verbatim — the
   subagent never reads this file. Tell it to work only in the named paths,
   follow the plan literally, not redesign or expand scope, and report back
   instead of guessing if the plan is wrong.

   **OpenSpec repos.** A repo that uses the OpenSpec lifecycle goes through its
   own skills: `openspec-propose` (seeded with the plan) to generate the change
   artifacts, which you check against the contract before coding;
   `openspec-apply-change` to implement by working through the change's task
   list, checking tasks off — nothing outside the list; if the work needs more,
   update the artifacts first; and `openspec-archive-change` **before** that
   repo is committed (step 8), so the archive lands in the same commit.

   **Decision notes.** Each implementer ends its report with one note per
   logical change: the file (repo-relative), a short distinctive `match` string
   from that hunk (a method or identifier name), what changed, why it was done
   this way (tied to the plan), alternatives rejected, and the risks and tests
   covering it. Notes come from the plan or from real choices made, never
   invented afterwards. Later fixes get notes too. They become the report's
   `explanations`.

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
   isolated working copies — see `### Implement` under `## Parallel mode`. A
   plan with a single task runs this step exactly as written.

6. **Run the gate (gate model).** Read `references/verification.md` and follow
   it. If the project defines a verification command — a gate, test, lint or
   build script, or a gate documented in the repo — dispatch a subagent with
   `model` = the **gate** model to run the **full** gate, not a convenient
   subset, and report its outcome faithfully. Beyond it, **every** changed
   repo's whole unit and integration suite runs (fast stage, then slow stage),
   its whole automation suite and the new automation test run against the
   local stack, and the behavior is verified in the browser with Claude in
   Chrome wherever it has a UI path — bringing the local stack up per the
   profile when it is not running. Record each as a report test row with its
   exact command, and every screenshot as evidence. It all MUST pass
   end-to-end; do not proceed otherwise. A genuine failure is a real defect to
   surface and fix (with the work model), never something to work around or
   paper over. If the repo defines no verification command, note that and run
   the suites directly.

   A full gate can outrun a foreground command timeout — a cold container build, a
   large test matrix, an e2e suite. Run it in the background and wait on
   completion rather than polling blindly or trimming stages to fit. Where the
   repo has no CI, this local run is the only verification the change will ever
   get; treat it accordingly. Keep the passing run's tail — it is the gate
   evidence step 10 puts in the change request or the merge note.

   Some gates distinguish a stage's outcome into more than plain pass/fail —
   e.g. an e2e/integration stage that can report the environment itself was
   unreachable (no daemon, registry egress blocked, stack never came up)
   separately from the suite actually running and failing. When the gate makes
   that distinction, handle the three outcomes differently:

   - **Passed for real:** proceed; no note needed.
   - **Environment-blocked** (the stage never actually ran against real
     infrastructure): the cycle MAY proceed, but you MUST record the reason and
     surface it in the commit at step 8 and in the change request or merge note
     at step 10. Never treat it as a shortcut.
   - **Genuine failure** (the stage ran and failed): a real implementation
     problem, never reclassified as environment-blocked — go back to step 5 to
     fix it, then re-run **the whole gate**, not just the stage that failed. An
     earlier stage can regress on the fix, and only a full green run is evidence.

   The automation suite and browser verification are never environment-blocked
   by a local service that is merely not started: starting it is part of this
   step (`references/verification.md`).

   A failure that looks incidental rather than caused by the change — a registry
   hiccup mid-build, a container that never became healthy, a process killed under
   host memory pressure — may be re-run **once** before it is treated as real. A
   test that actually executed and failed its assertion is real on the first run;
   never re-roll one of those hoping for a different answer.

   A genuine gate failure stops the cycle here; do not continue to the intent
   gate or the commit on a red gate.

   With `--parallel`, the gate run is unchanged, but fixes for failures in
   separate tasks run concurrently — see `### Gates` under `## Parallel mode`.

7. **The intent gate and code review.** First run `/code-review` (through the
   Skill tool) on each repo's diff at effort `low` or `medium` — never higher —
   and fix real findings with the work model.

   Then dispatch a **fresh subagent** that did not do the
   implementation, under the `review:` model (default opus). Give it exactly two
   things: the work source's contract — the ticket's description plus the
   intent-contract comment, or the roadmap item's verbatim text, or the work
   description plus the plan from step 4 — and the diff of every changed repo
   against its base (committed plus uncommitted).

   Ask it to return a verdict per acceptance criterion — `satisfied` with the
   file and line that satisfies it, or `not satisfied` with what is missing —
   plus any change in the diff that no criterion asked for, and any regression
   or new bug it sees. Instruct it to default to `not satisfied` when it cannot
   find the evidence.

   - **Any criterion unmet** → back to step 5 to finish the work, then re-run the
     verification gate and this gate. Do not commit and do not open a change
     request on an unmet criterion.
   - **Unrequested scope in the diff** → remove it, or justify it at step 10 as
     necessary to the change (a refactor the fix required, a test a criterion
     implies).

   Cap the review-and-fix loop at three cycles; anything still open after the
   third is escalated (`## Escalation and stop`). Record each cycle's findings
   and fixes in the report's `review`.

   Hold the verdict table: step 10 puts it in the change request or the
   closing comment.

   With `--parallel`, the criteria are split across concurrent reviewers plus
   one scope reviewer — see `### Gates` under `## Parallel mode`.

8. **Prepare the commit, then commit.** For an OpenSpec repo, archive the
   change now (step 5). Confirm each repo's working copy holds no stray files,
   secrets, or generated artifacts. Draft the message with
   `/arbor-code-gencommit <ID>` (it reads the uncommitted diff), then shape it as
   below.

   If a valid `roadmap:` reference was supplied, flip the item
   before authoring the commit — reaching this step is itself the
   precondition, since a genuine gate failure already stopped the cycle at
   step 6 and an unmet acceptance criterion already stopped it at step 7.
   Re-confirm the target line is still `- [ ] **R<n>**`, then change only that
   marker to `- [x] **R<n>**`, leaving the item's text and wrapped
   continuation lines byte-identical. Then test the whole file: if no
   `- [ ] **R<m>**` line survives for any item `<m>` — not just the one you
   flipped — the roadmap is complete, so create `docs/roadmaps/archive/` if it
   isn't there yet and move the file into it (the VCS's tracked move); the flip
   already landed, so the archived copy carries the checked box. If any item is
   still unchecked, leave the file at `docs/roadmaps/<slug>.md`. Include the
   flip and any move in the same commit as the work, on the same branch — no
   separate bookkeeping commit or push. Under `--manual`, make the flip (and
   any move) in the working copy so the user's commit carries it.

   With `--parallel`, first fold the wave checkpoint commits back into the
   working changes (the VCS's fold, to the point the branch was created from),
   so the cycle still lands as a single commit.

   Commit with a subject `{ID} {short description}` (the uppercase work ID —
   the ticket key when there is one — e.g. `PROJ-4 add cart`), optionally
   followed by a blank line and `-` bullets for detail. In workspace mode every
   changed repo gets its own commit with the same subject. Follow the repo's
   and the profile's commit conventions if documented. If step 6 reported an
   environment-blocked stage — which still reaches the flip and
   any archival above — add a bullet surfacing it, e.g. `- E2E skipped:
   environment-blocked (<reason>); not independently verified.` If a
   `roadmap:` reference was supplied, add `- Roadmap: <slug> R<n> complete`
   (`<slug>` is the roadmap filename without its `.md` extension); if the flip
   also archived the file, additionally add `- Roadmap <slug> complete;
   archived`. In ticket mode, when the work ID is not the ticket key, add a
   `Ticket: <ref>` line. If the code host closes tickets from a keyword **and
   this cycle merges straight to the base branch**, add the keyword line so
   the merge closes the ticket; when the work lands through a change request
   instead — `--pr`, interactive, or an autonomous self-merge in a repo that
   integrates through change requests — it belongs in the change request at
   step 10, not here. All of these bullets are independent and may appear
   together in one commit body.

   **Under `--manual`, do not commit.** Put the finished message in the
   report's `commitMessage` (a string, or an object keyed by repo name when
   repos need different messages), publish the report (step 9's report part),
   and finish with the summary at the end of step 10. Never stage, commit or
   push, and never open a change request.

9. **Push, then publish the report.** Push the branch (every changed repo's, in
   workspace mode) and mark each repo `"pushed": true` in the report. Then fill
   the rest of `report.json` — explanations from the Decision notes, manual
   tests, evidence, setup, follow-ups, `testManagement` only when step 0
   enabled it — and generate, serve and open the page as
   `references/report.md` describes, **before** integrating (integration
   changes the diff base the page is built from). Fix every `explanation match
   not found` warning and every manual-test environment warning before showing
   it.

10. **Integrate and close out.** Autonomous: merge to the base branch (the
    repo's default branch, or each workspace repo's `baseBranch`) — unless
    `--pr` was passed, in which case open a change request instead of merging.
    Interactive: ask for approval, then open a change request. Where the
    profile names a different integration route, follow it. In workspace mode,
    integrate the repos in the plan's dependency order (e.g. schema changes
    first).

    Where the repo integrates through change requests, an autonomous cycle
    still goes through one — open it, then self-merge it, deleting the branch.
    That is a self-merge, not a review request: no human approves it, and the
    change request exists to carry the record. A closing keyword then lives in
    the change request rather than the commit, and closes the ticket when the
    merge lands.

    Where the repo ships a change-request template, fill it; otherwise the
    description carries the ticket reference (and the host's closing keyword,
    where it has one), the step 7 verdict table mapping each acceptance
    criterion to the code that satisfies it, the gate evidence from step 6
    (including any environment-blocked stage and its reason), and the
    assumptions from the intent contract.

    If a merge conflicts, rebase onto the base branch, then re-run **both**
    gates — step 6's verification gate in full and step 7's intent gate — before
    merging. A rebased branch is unverified until it is re-gated.

    In ticket mode, **close out** once the work has landed: switch to the base
    branch and update it; confirm the ticket is closed and **close** it if the
    merge did not; **swap labels** from working to done; and **comment** with
    the change request or commit link, the criteria table, the report summary,
    and follow-ups worth filing.

    Follow-ups are *reported* in that comment for the developer to triage. Never
    file them as tickets yourself.

    **Finish with a short summary in the session:** the ticket as understood,
    repos changed and their branches, tests added (including automation),
    verification evidence, the review outcome, anything left for the user, and
    the ticket page and all-tickets index URLs. Under `--manual`, say plainly
    that nothing was committed or pushed, and that the user commits and pushes
    (and, when enabled, publishes tests to the test-management system) from
    the report page.

## Code standards

Step 5's dispatch prompt MUST carry this section verbatim — the subagent never
reads this file.

**The code is the documentation.** Meaning lives in intention-revealing names,
functions small enough to do one thing, signatures and types that state the
contract, and control flow shallow enough to read top to bottom. Effort that
would go into explaining a confusing block goes into making the block
unconfusing. A comment is never a substitute for a clearer name or a smaller
function. Match the surrounding code's style, naming and comment density.

**A comment earns its place only by carrying what the code cannot:** why a
non-obvious approach beat the obvious one, a constraint imposed from outside (a
protocol quirk, an upstream bug, a measured performance trade-off), or a warning
about a consequence a reader would not predict. Public-API doc comments follow
whatever convention the repo already uses.

Everything else stays out: no narration of what the next line does, no
step-by-step running commentary, no change-name or ticket references, no
restating a task from the plan, no banner comments labelling sections that names
already label. The record of *what changed and why* lives in the commit and the
change request — not in the source.

Judge the result by the code, not by its annotations. Heavily commented code a
reader still has to decode has failed this standard; uncommented code that reads
plainly has met it.

## Escalation and stop

Escalating is a legitimate outcome, not a failure — but it costs the developer
attention, so spend it only on ambiguity with no defensible default, or on a
blocker you genuinely cannot clear. Leave a durable, self-contained record: what
you were doing, what specifically is ambiguous or broken, what you already tried,
and the **numbered specific questions** you need answered.

In ticket mode that record is a ticket comment plus the needs-clarification
label, with the working label removed. Use the blocked label instead when the
intent is clear but the gate will not pass, and paste the actual failure
output. If you got as far as working code, push the branch and open a **draft**
change request so the work is not lost. Unassign yourself either way.

Under `--manual`, or without a ticket, there is nothing to label: report the
same record in the session — and in the report's `hiccups` and `followups`,
publishing the page so far — and stop. A caller that dispatched this cycle owns
the bookkeeping for a cycle that did not ship, and reads the outcome you return.

In every case, notify the developer out of band with `PushNotification` — a
comment alone will not reach them on a loop that runs unattended. Then stop. Do
not guess and merge.

## Parallel mode

`--parallel` cuts the wall-clock time of one cycle by fanning agents out inside
steps 4–7 wherever the work splits. It changes nothing the cycle ships: both
gates still pass on the merged result, and the cycle is still one work ID, one
branch, one work source, and one commit per repo. Steps 0–3 and 8–10 run as
written. It composes with every other flag and reference. In workspace mode the
waves apply within each repo; separate repos already get separate implementers.

It trades tokens for time — scouts, parallel reviewers, and per-copy
dependency installs all cost more than the sequential cycle.

**Mechanics.** The session running this skill is the **orchestrator**: it
dispatches, validates, merges, and combines results, and never implements.
Agents that run concurrently are dispatched **in a single message**, and all of
them are awaited before moving on. The concurrency cap bounds every fan-out; a
larger fan-out runs in batches of at most the cap.

### Plan

**Scouts** (`scout:` model, concurrent). From the step 1 contract and a cheap
map of the repo — its tracked files grouped by top-level directory, plus
`CLAUDE.md` and `docs/CONVENTIONS.md` if present — pick up to *cap* areas worth
reading: the packages or directories the contract touches, and where their
tests live. A narrow slice or a small repo gets one scout. Each scout reads only
its area, **writes nothing**, and returns at most ~400 words:

- the relevant files, by path;
- key types and signatures, and existing patterns to reuse;
- where the area's tests live, and the command that runs only them;
- shared plumbing it saw — registries, barrel or index files, routing tables,
  config, package manifests, lockfiles.

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

1. **Dispatch.** One agent per task, each in an isolated working copy (the
   Agent tool's `isolation: "worktree"` where the VCS supports it, otherwise
   the VCS mapping's isolated working copy) with `model` = the `work:` model.
   Each copy starts from the feature branch's current tip, so it holds every
   earlier wave. Each agent receives the full plan, its own task ID and owned
   files, the VCS mapping, and the **Code standards** section verbatim, plus
   these rules:
   - edit only owned files — if the task cannot be done without touching
     another file, stop and report a blocker instead;
   - run the task's `test:` command until it passes; never run the full gate;
   - commit in its copy as `wip <task-id>`, then report the branch, the commit
     identifier, the changed files, the tail of the test output, and its
     Decision notes.
2. **Dependencies.** A fresh copy has no installed dependencies. If the main
   checkout has a dependency directory (`node_modules`, `.venv`, `vendor`, …)
   and the wave changes no lockfile, the agent symlinks it from the main
   checkout; otherwise it runs the repo's install command in its copy. The W1
   dependency task always installs for real.
3. **Ownership check.** For each task, list the files changed between the wave
   base and its commit. A file outside the task's ownership rejects it:
   re-dispatch it **once**, naming the offending files. A second stray is a
   blocker.
4. **Merge.** Merge each task branch into the feature branch in task order.
   Disjoint ownership rules out a textual conflict; if one occurs anyway, it is
   a blocker. Then run the union of the wave's `test:` commands on the merged
   tree, one after another, to catch tasks that pass alone but break together.
   A failure there gets one fix agent on the merged tree in the main checkout,
   then the wave's tests run again.
5. **Checkpoint.** Commit the merged wave on the feature branch as a checkpoint;
   the next wave starts from it. Remove each copy once its branch has merged.
   Under `--manual`, after the last wave fold the checkpoints back to the point
   the branch was created from, so the work is left uncommitted for the user.

If any agent in a wave reports a blocker, let the rest of the wave finish,
merge **nothing** from that wave, and escalate per `## Escalation and stop` —
push the branch holding the completed waves, open a draft change request, label
the ticket, and notify (under `--manual`: record it in the report and stop,
without pushing).

### Gates

**Verification gate.** Step 6's run is unchanged: one `gate:` agent runs the
**full** command on the merged branch. Never shard or subset the gate; making
the command itself faster is the project's concern. On failure, the gate agent
reports each failure with the files it implicates, and the orchestrator maps
them to tasks by ownership:

- failures in distinct tasks get **one fix agent per task, concurrently**,
  under the `### Implement` rules — isolated copy, owned files only, the task's
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

## Guardrails

- **Never integrate work that has not passed both gates.** A partial gate is a
  failing gate, and a green gate on the wrong feature is a failed cycle.
- **Every suite runs whole.** No filtered or cached test runs, no skipped
  automation row, no browser check skipped because a service was not started
  (`references/verification.md`). Never write `passed` for a run that did not
  happen in this session.
- **No provider is hardcoded.** Ticket system, code host and VCS commands come
  only from their mappings (`## Providers`); a mapping built at runtime is
  proven read-only before anything writes through it.
- **The plan writes no files in the repos.** It is session state threaded into
  the implementation and saved to the work dir for the report — never a
  proposal, spec, or task artifact committed to a repo, except through a repo's
  own OpenSpec lifecycle.
- **Under `--manual`, never stage, commit, push, or open a change request**,
  and never write to the ticket. The user commits from the report.
- **The report is generated, not hand-written**, from `report.json` through
  `report/build_report.py`, and it is shown to the user every time a new
  version is served. Test-management publishing is enabled only when the
  skill its mapping names is in the session.
- **Test data is created for the cycle.** Never reuse accounts or records
  quoted in a ticket, never modify data you did not create, and never write
  passwords or tokens into files, the report, or commits.
- The roadmap flip, the ticket close-out, and any archival happen only because
  their step was reached — never as bookkeeping independent of the gate outcomes.
- A gate stage may only be treated as skipped when it itself reports an
  environment-blocked outcome — never as a shortcut, and never for a genuine
  failure against infrastructure that did come up. When step 6 reports one, that
  skipped stage MUST leave a visible trace (commit bullet, and change request or
  merge note if applicable) — never merge unverified changes silently.
- **Reject malformed model tokens.** An unknown phase key or model name stops the
  run at step 0, before any branch exists or any ticket is claimed — never
  silently drop it or substitute a default.
- **Each phase completes before the next begins.** Without `--parallel`, a
  phase is one synchronous subagent (one per repo in workspace mode); with it,
  a phase may fan out concurrent agents, dispatched in one message and all
  awaited before the next phase.
- **Always dispatch each phase as a subagent** carrying its phase's
  model, and always pass the plan and the code standards into the implementation
  dispatch.
- **The project profile adds rules, never removes gates.** Its hard rules bind
  this cycle; nothing in it can skip a suite or the intent gate.
- **Never author or re-scope tickets or roadmap items.** You claim them, build
  them, and close them; the developer writes them. Follow-up work is reported in
  a comment, never filed as new work by you.
- **Describe the project on its own terms.** Never position or explain it by
  naming or comparing against another software product — not in code, docs,
  commits, tickets, or change requests. Naming a tool the project actually
  depends on or is migrating from is ordinary and fine; framing the project as
  an alternative to something else is not.
- One change = one work ID = one branch = one work source. Keep them in sync, and
  never batch two tickets or two roadmap items into one cycle.
