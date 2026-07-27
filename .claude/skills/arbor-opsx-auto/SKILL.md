---
name: arbor-opsx-auto
description: Use when a described unit of work should run through the entire OpenSpec lifecycle — propose, apply, best-effort gate, archive — in one pass on the current branch, leaving changes uncommitted (no work-ID, branch, commit, push, or merge). Each phase runs as a subagent under a per-phase model (defaults spec=opus, work=sonnet, gate=haiku, archive=haiku), overridable with spec:/work:/gate:/archive: tokens. Defaults to fully autonomous; pass --interaction to approve before apply and before archive. arbor-auto-work delegates its lifecycle to this skill.
license: MIT
metadata:
  author: arbor
  version: "2.0"
---

# Arbor OpenSpec auto lifecycle

Take a unit of work through the whole OpenSpec lifecycle in one pass:
**propose → apply → gate → archive**. It chains the `openspec-propose`,
`openspec-apply-change`, and `openspec-archive-change` skills, running the
project's verification gate between apply and archive.

This skill is a **thin orchestrator**: each phase runs in its own subagent so it
can carry its own model (see **Model selection**). The orchestrator parses the
model selection, sequences the phases, handles the interactive approval gates,
and reads each subagent's reported outcome to decide whether to continue.

**Announce at start:** "Using arbor-opsx-auto to run the OpenSpec lifecycle."

## Modes

- **autonomous** (default): proceed through every step without prompts.
- **interactive** (`--interaction`): ask for approval before **apply** and
  before **archive**. Everything else still runs unattended. Because the phases
  run in subagents (which cannot prompt mid-run), these two approval gates are
  handled by this orchestrator *between* subagent dispatches.

## Model selection

Every phase runs as a subagent dispatched with an explicit `model`. The four
accepted model names are exactly the Agent tool's `model` values — `opus`,
`sonnet`, `haiku`, `fable` — passed straight through; the skill never resolves
concrete model ids itself. Each phase has a default tier, used when the caller
does not override it:

| Knob       | Phase (delegated skill / action)       | Default  |
|------------|----------------------------------------|----------|
| `spec:`    | `openspec-propose`                     | **opus**   |
| `work:`    | `openspec-apply-change`                | **sonnet** |
| `gate:`    | run the project's verification command | **haiku**  |
| `archive:` | `openspec-archive-change`              | **haiku**  |

**Syntax.** Bare tokens (primary) or a `--models` list — both parse identically:

```
<description> spec:opus work:sonnet
<description> --models spec:opus,work:sonnet
```

**Parsing.**

- A token matching `^(spec|work|gate|archive):(opus|sonnet|haiku|fable)$` — or a
  comma-separated list of them behind `--models` — is a model assignment and is
  removed from the input.
- After removing model tokens and the `--interaction` flag, whatever remains is
  the `WORK_DESCRIPTION`.
- An **unknown phase key or model name** (e.g. `wrok:sonnet`, `spec:opua`) is a
  hard error: **stop and report** it. Never silently ignore a mistyped override
  or fall back to a default in its place.
- Unspecified phases use their default tier from the table above.

## Execution

Each phase is dispatched to a **general-purpose subagent** with the phase's
resolved `model`, instructed to run its delegated skill (or, for the gate, the
verification command) **autonomously**. Dispatch every phase **synchronously**
(`run_in_background: false`) — each phase depends on the previous one's file
changes and its reported outcome. Subagents share this working directory, so each
phase sees the artifacts and edits the prior phase produced (propose writes the
artifacts → apply implements against them → archive moves them). The orchestrator
threads only the resolved `CHANGE_NAME` (and, for propose, the
`WORK_DESCRIPTION`) into each subagent's prompt.

## Inputs

- `WORK_DESCRIPTION` (required) — the slice of work to build (the input with all
  model tokens and flags removed).
- `CHANGE_NAME` (optional) — an explicit change name to use verbatim (e.g.
  `arbor-auto-work` passes its `<TYPE>-<n>-<slug>` work ID). If omitted, derive a
  kebab-case name from the description.
- Model tokens (optional) — `spec:`/`work:`/`gate:`/`archive:` assignments as
  above, bare or behind `--models <list>`.
- `--interaction` (optional flag) — enable the interactive mode above.

## Scope — what this skill does NOT do

It runs on the **current branch** and **leaves every change uncommitted** — the
new artifacts, the implementation, and the archive move. It assigns no work ID
and does not create a branch, commit, push, or merge. If you need any of that,
use `arbor-auto-work`, which wraps this skill with the work-ID/branch/commit/
push/integrate cycle.

## Workflow

```
parse models → resolve name →
  [spec model]    propose → [approve?] →
  [work model]    apply → [gate model] gate → tasks complete? → [approve?] →
  [archive model] archive → report
```

## Steps

You MUST create a todo per step and complete them in order.

1. **Parse model selection.** Extract any `spec:`/`work:`/`gate:`/`archive:`
   tokens (bare or behind `--models`) per **Model selection**. Reject an unknown
   phase key or model name with a hard error — stop and report. Fill unspecified
   phases with their defaults (spec=opus, work=sonnet, gate=haiku, archive=haiku).
   Hold the resolved four-way model map for the dispatches below, and strip these
   tokens (and `--models`) from the input to leave the `WORK_DESCRIPTION`.

2. **Resolve the change name.** Use `CHANGE_NAME` if provided; otherwise derive a
   kebab-case name from `WORK_DESCRIPTION` (e.g. "add retry to payments" →
   `add-payment-retry`). Hold this name for every phase below.

3. **Propose (spec model).** Dispatch a subagent with `model` = the **spec**
   model, instructing it to invoke the `openspec-propose` skill autonomously with
   the resolved change name and the work description. Because the name is
   supplied, propose creates the change (`openspec new change "<name>"`) and
   generates all artifacts — proposal, design, specs, tasks — without stopping to
   ask what to build. Read back its confirmation.

4. **Approval before apply (interactive only).** If `--interaction`, summarize
   the proposed change and ask for approval to implement. Autonomous: skip.

5. **Apply (work model).** Dispatch a subagent with `model` = the **work** model,
   instructing it to invoke `openspec-apply-change` autonomously with the
   explicit change name. It implements every task, following the repo's
   conventions if present (`CLAUDE.md`, `docs/CONVENTIONS.md`): narrow
   directories, concise files, reuse, extension, tests beside source. If apply
   hits a genuine blocker (ambiguous task, error), it reports that back instead
   of a clean completion — treat that as a real problem and stop, per the
   guardrails.

6. **Run the gate (gate model).** If the project defines a verification command —
   an `npm run gate` / test / lint / build script, or a gate documented in the
   repo — dispatch a subagent with `model` = the **gate** model to run it and
   report the outcome. It MUST pass end-to-end; do not proceed otherwise. If the
   repo defines no such command, note that and continue.

   Some gates distinguish a stage's outcome into more than plain pass/fail —
   e.g. an e2e/integration stage that can report the environment itself was
   unreachable (no daemon, registry egress blocked, stack never came up)
   separately from the suite actually running and failing. When the gate
   makes that distinction, handle the three outcomes differently:
   - **Passed for real:** proceed to archive; no note needed.
   - **Environment-blocked** (the stage never actually ran against real
     infrastructure): the lifecycle MAY proceed to archive, but you MUST
     **record the reason and surface it in the final report** so whoever commits
     (the user, or `arbor-auto-work`) can note that this stage was not verified
     and why. Never treat it as a shortcut.
   - **Genuine failure** (the stage ran and failed): a real implementation
     problem, never reclassified as environment-blocked — **stop and report**;
     do not archive.
   If the gate makes no such distinction, a pass is a pass and a failure stops
   the lifecycle.

7. **Confirm tasks complete.** Read `tasks.md` and confirm every task is `- [x]`.
   If any `- [ ]` remain, **stop and report** rather than archiving incomplete
   work.

8. **Approval before archive (interactive only).** If `--interaction`, ask for
   approval to archive. Autonomous: skip.

9. **Archive (archive model).** Dispatch a subagent with `model` = the
   **archive** model, instructing it to invoke `openspec-archive-change`
   autonomously with the explicit change name. Because the name is known and all
   tasks are complete, its change selection and completion prompts are already
   satisfied. The subagent takes the recommended **delta-spec sync** default
   ("Sync now") — because it runs in a subagent, that fine-grained prompt does
   not surface even in `--interaction`; the step-8 gate is the interactive
   checkpoint for archiving.

10. **Report.** Print the outcome, including the resolved per-phase models.
    **Do not commit** — leave the working tree for the caller.

## Autonomy contract

Because this skill always holds a concrete change name, every delegated opsx
skill (run inside its phase subagent) is passed that name, so none of them stops
to ask *which* change to act on. In autonomous mode, any remaining
recommended-default prompt inside a delegated skill (notably archive's spec-sync
choice) is answered with its recommended default without stopping. Genuine
blockers — apply failure, a real gate failure, or incomplete tasks — always stop
the run and are reported. A malformed model token stops the run before any phase
is dispatched. Autonomy never means archiving broken or unverified work.

## Output

```
## OpenSpec lifecycle complete

**Change:** <change-name>
**Location:** openspec/changes/archive/YYYY-MM-DD-<change-name>/
**Mode:** autonomous | interactive
**Models:** spec=<model> work=<model> gate=<model> archive=<model>

### Code changes
- Modified: <file>, <file>
- Created: <file>

### Artifacts
- ✓ proposal.md / design.md / specs / tasks.md (all tasks complete)

### Gate
- <passed | environment-blocked: reason | no gate defined>

Working tree left uncommitted. Commit when ready (or let arbor-auto-work handle it).
```

## Guardrails

- **Never commit, branch, push, or merge** — this skill ends with the archive
  move and an uncommitted working tree.
- **Never archive broken or unverified work.** A genuine gate failure or any
  incomplete task stops the lifecycle.
- **Never silently skip verification.** An environment-blocked gate stage may
  proceed, but only with the reason surfaced in the report so the committer can
  note it.
- **Reject malformed model tokens.** An unknown phase key or model name stops the
  run before any phase is dispatched — never silently drop it or substitute a
  default.
- **Always dispatch each phase as a synchronous subagent** carrying its phase's
  model, and **always pass the explicit change name** into that subagent so the
  delegated opsx skill runs without prompting.
- **One run = one change.** For work that needs several changes, run the skill
  once per change (or use `arbor-auto-work` per slice).
