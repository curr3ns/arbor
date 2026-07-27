---
name: arbor-opsx-auto
description: Use when a described unit of work should run through the entire OpenSpec lifecycle — propose, apply, best-effort gate, archive — in one pass on the current branch, leaving changes uncommitted (no work-ID, branch, commit, push, or merge). Defaults to fully autonomous; pass --interaction to approve before apply and before archive. arbor-auto-work delegates its lifecycle to this skill.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor OpenSpec auto lifecycle

Take a unit of work through the whole OpenSpec lifecycle in one pass:
**propose → apply → gate → archive**. It chains the `openspec-propose`,
`openspec-apply-change`, and `openspec-archive-change` skills, running the
project's verification gate between apply and archive.

**Announce at start:** "Using arbor-opsx-auto to run the OpenSpec lifecycle."

## Modes

- **autonomous** (default): proceed through every step without prompts.
- **interactive** (`--interaction`): ask for approval before **apply** and
  before **archive**. Everything else still runs unattended.

## Inputs

- `WORK_DESCRIPTION` (required) — the slice of work to build.
- `CHANGE_NAME` (optional) — an explicit change name to use verbatim (e.g.
  `arbor-auto-work` passes its `<TYPE>-<n>-<slug>` work ID). If omitted, derive a
  kebab-case name from the description.
- `--interaction` (optional flag) — enable the interactive mode above.

## Scope — what this skill does NOT do

It runs on the **current branch** and **leaves every change uncommitted** — the
new artifacts, the implementation, and the archive move. It assigns no work ID
and does not create a branch, commit, push, or merge. If you need any of that,
use `arbor-auto-work`, which wraps this skill with the work-ID/branch/commit/
push/integrate cycle.

## Workflow

```
resolve name → propose → [approve?] → apply → gate → tasks complete? → [approve?] → archive → report
```

## Steps

You MUST create a todo per step and complete them in order.

1. **Resolve the change name.** Use `CHANGE_NAME` if provided; otherwise derive a
   kebab-case name from `WORK_DESCRIPTION` (e.g. "add retry to payments" →
   `add-payment-retry`). Hold this name for every delegated skill below.

2. **Propose.** Invoke the `openspec-propose` skill, passing the resolved change
   name and the work description. Because the name is supplied, it creates the
   change (`openspec new change "<name>"`) and generates all artifacts —
   proposal, design, specs, tasks — without stopping to ask what to build.

3. **Approval before apply (interactive only).** If `--interaction`, summarize
   the proposed change and ask for approval to implement. Autonomous: skip.

4. **Apply.** Invoke the `openspec-apply-change` skill with the explicit change
   name. Implement every task, following the repo's conventions if present
   (`CLAUDE.md`, `docs/CONVENTIONS.md`): narrow directories, concise files,
   reuse, extension, tests beside source. If apply hits a genuine blocker
   (ambiguous task, error), it pauses — treat that as a real problem and stop,
   per the guardrails.

5. **Run the gate.** If the project defines a verification command — an
   `npm run gate` / test / lint / build script, or a gate documented in the
   repo — run it. It MUST pass end-to-end; do not proceed otherwise. If the repo
   defines no such command, note that and continue.

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

6. **Confirm tasks complete.** Read `tasks.md` and confirm every task is `- [x]`.
   If any `- [ ]` remain, **stop and report** rather than archiving incomplete
   work.

7. **Approval before archive (interactive only).** If `--interaction`, ask for
   approval to archive. Autonomous: skip.

8. **Archive.** Invoke the `openspec-archive-change` skill with the explicit
   change name. Because the name is known and all tasks are complete, its change
   selection and completion prompts are already satisfied. For its **delta-spec
   sync** choice: autonomous mode selects the recommended default ("Sync now")
   without prompting; `--interaction` lets that prompt surface.

9. **Report.** Print the outcome. **Do not commit** — leave the working tree for
   the caller.

## Autonomy contract

Because this skill always holds a concrete change name, every delegated opsx
skill is passed that name, so none of them stops to ask *which* change to act
on. In autonomous mode, any remaining recommended-default prompt inside a
delegated skill (notably archive's spec-sync choice) is answered with its
recommended default without stopping. Genuine blockers — apply failure, a real
gate failure, or incomplete tasks — always stop the run and are reported.
Autonomy never means archiving broken or unverified work.

## Output

```
## OpenSpec lifecycle complete

**Change:** <change-name>
**Location:** openspec/changes/archive/YYYY-MM-DD-<change-name>/
**Mode:** autonomous | interactive

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
- **Always pass the explicit change name** to each delegated opsx skill so it
  runs without prompting.
- **One run = one change.** For work that needs several changes, run the skill
  once per change (or use `arbor-auto-work` per slice).
