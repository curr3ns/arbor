---
name: arbor-opsx-reconcile
description: Use when code already exists but no OpenSpec change ever described it — work built ad hoc, a diff inherited from elsewhere, or spec history that needs backfilling before the work can be reviewed. Reconciles the uncommitted working tree (or an explicit ref range) into one or more archived OpenSpec changes whose artifacts read as though they had generated the code, splitting unrelated work into separate changes, verifying before it archives, and never editing the code it documents. Leaves everything uncommitted. The inverse of arbor-opsx-auto.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor OpenSpec reconcile

Run the OpenSpec lifecycle **backwards**. Start from a diff that already exists
and produce the spec record that would have produced it — proposal, delta specs,
design, tasks — then gate it, archive it, and sync the deltas into
`openspec/specs/`. `arbor-opsx-auto` turns a description into code; this skill
turns code into the description that should have preceded it, and leaves the end
state indistinguishable from a change that ran forward.

**Announce at start:** "Using arbor-opsx-reconcile to reconcile the current diff
with OpenSpec."

## The rule that outranks every other instruction here

**This skill writes only under `openspec/`.**

It never edits, reformats, renames, reverts, or "tidies" a single line of the
code it is documenting — not to make a requirement cleaner, not to fix a bug it
notices, not to satisfy its own coverage check. The diff is the ground truth and
the artifacts bend to it. Step 6 verifies this mechanically and fails the run if
anything outside `openspec/` moved.

If the code is wrong, say so in the report and leave it wrong.

## Inputs

- *(no argument)* — reconcile the **uncommitted working tree**: tracked
  modifications against `HEAD` plus untracked files. This is the default and the
  normal case.
- `<ref-range>` (optional) — reconcile committed work instead, e.g. `main..HEAD`
  or `HEAD~3..HEAD`. Anything that `git diff` accepts as a range.
- `--single` (optional flag) — force one change and skip the split in step 3.
- `INTENT_HINT` (optional free text) — whatever remains after the tokens and
  flags are stripped. Treat it as first-hand testimony about *why* the change was
  made, outranking anything inferred in step 5. Its absence is normal.
- Model tokens (optional) — `spec:`/`check:`/`gate:`/`archive:` assignments,
  bare or behind `--models <list>`.

## Model selection

Same grammar as `arbor-opsx-auto`. The four accepted model names are exactly the
Agent tool's `model` values — `opus`, `sonnet`, `haiku`, `fable` — passed
straight through; never resolve concrete model ids.

| Knob       | Phase                                       | Default  |
|------------|---------------------------------------------|----------|
| `spec:`    | author one slice's artifacts                | **opus**   |
| `check:`   | coverage check one slice's artifacts        | **sonnet** |
| `gate:`    | run the project's verification command      | **haiku**  |
| `archive:` | archive one slice and sync its delta specs  | **haiku**  |

```
<hint> spec:opus check:sonnet
<hint> --models spec:opus,check:sonnet
```

A token matching `^(spec|check|gate|archive):(opus|sonnet|haiku|fable)$` — or a
comma-separated list behind `--models` — is a model assignment and is removed
from the input. An **unknown phase key or model name** (e.g. `chek:sonnet`,
`spec:opua`) is a hard error: **stop and report** before doing anything else.
Never silently ignore a mistyped override or substitute a default for it.

`spec:` and `check:` must not resolve to the same model unless the caller asked
for that explicitly — see step 5b.

## Scope — what this skill does NOT do

It runs on the **current branch** and **leaves every change uncommitted**: the
new artifacts, the archive moves, and the synced specs all sit in the working
tree for the caller. It assigns no work ID and does not create a branch, commit,
push, or merge. It writes no code. If you need the commit/branch/integrate cycle,
that is `arbor-auto-work`; if you need code built from a description, that is
`arbor-opsx-auto`.

## Workflow

```
parse input → snapshot the diff → [gate] verify the tree → split into slices → order slices
  per slice, sequentially:
     [spec]    author artifacts (every task pre-checked)
     [check]   coverage check — fresh eyes, one retry
     [archive] archive + sync delta specs
→ verify nothing outside openspec/ moved → report
```

## Steps

You MUST create a todo per step and complete them in order.

### 0. Parse the input

Extract the model tokens per **Model selection** (hard error on an unknown key or
model name), then the `--single` flag, then an optional ref range. Whatever
remains is the `INTENT_HINT`. Fill unspecified phases with their defaults.

### 1. Snapshot the diff

Everything downstream reads this snapshot, **never** live `git` output — later
steps mutate the working tree by adding files under `openspec/`, so re-deriving
the diff mid-run would show a moving target and silently change what the slices
mean. Write to the session scratchpad:

```bash
SNAP="<scratchpad>/reconcile"
mkdir -p "$SNAP"

# Source diff — working tree (default) or the given range
git diff HEAD > "$SNAP/diff.patch"                       # or: git diff <range>
git status --porcelain > "$SNAP/status.txt"
git ls-files --others --exclude-standard > "$SNAP/untracked.txt"

# Reconstructed intent evidence
git branch --show-current > "$SNAP/branch.txt"
git log --format='%h %s%n%b' <range> > "$SNAP/log.txt"   # range mode only

# Fidelity fingerprint — everything outside openspec/, re-checked in step 6
{ git diff HEAD -- . ':(exclude)openspec';
  git ls-files --others --exclude-standard -- . ':(exclude)openspec'; } \
  | shasum > "$SNAP/fingerprint.txt"
```

`git diff HEAD` does not include untracked files. Read each path in
`untracked.txt` directly and treat its full contents as an added file — an
untracked file is usually the *most* important part of a diff, since it is where
new capabilities live.

**Stop and report** if:

- the source diff and the untracked list are both empty — there is nothing to
  reconcile;
- `openspec/changes/` holds an active (non-archived) change directory — the tree
  already has an in-flight change, and reconciling around it would produce two
  competing records of the same work. Finish or delete that change first.

Modifications under `openspec/` that are already in the source diff are excluded
from the split and named in the report. Specs are not themselves specified.

### 2. Gate the whole tree (gate model)

Dispatch a subagent with `model` = the **gate** model to run the project's
verification command if one exists — an `npm run gate` / test / lint / build
script, or a gate documented in the repo — in **full**, not a convenient subset,
reporting the outcome faithfully.

The gate runs **once, here, before anything is archived**, not per slice: the
tree is never partially applied, so there is nothing slice-shaped to verify, and
an archived spec must never claim behavior that the code does not actually
deliver. Handle three outcomes:

- **Passed:** proceed.
- **Environment-blocked** (the stage never ran against real infrastructure — no
  daemon, egress blocked, stack never came up): MAY proceed, but you MUST record
  the reason and surface it in the final report.
- **Genuine failure:** **stop and report.** Archive nothing.

A failing gate may well be a pre-existing failure that this diff did not cause.
Do not try to find out — every way of checking (stashing, reverting, checking out
a clean tree) mutates the code, which is forbidden. Report the failure as it
stands and let the caller decide.

If the repo defines no verification command, note that and continue.

### 3. Split into slices (inline — do not delegate)

Read `diff.patch` in full — actual hunks, not just `--stat` — plus every
untracked file, and every `openspec/specs/*/spec.md`. Group the changes into
slices. Do this **yourself**, in this context: the split is the one decision that
requires seeing the whole diff at once, and a subagent given the whole diff to
split would just be this step in a smaller context window.

With `--single`, skip the grouping: one slice, everything in it.

**Group by behavioral concern, not by file.** Signals, in priority order:

1. **Existing capability boundaries.** Two files whose changes serve requirements
   of the same capability in `openspec/specs/` belong in the same slice.
2. **Mutual dependence.** If one file's change is meaningless without another's —
   a caller and its callee, a feature and the test that covers it, a flag and the
   code reading it — they are never split apart.
3. **Module and directory boundaries.** The weakest signal; use it only to break
   a tie the first two leave open.

Tests, fixtures, docs, and config travel with the behavior they serve. They never
form a slice of their own — a "docs" slice describes no capability and produces a
change proposal with nothing to propose.

A file belongs to exactly one slice. Splitting a single file's hunks across
slices is permitted only when the hunks are genuinely unrelated, and the report
must name the file and say why.

**Bias hard toward fewer, larger slices.** A coarse slice is one proposal that
covers a lot of ground — mildly untidy, entirely true. A wrong split is two
fabricated histories, each claiming work the other did, and each archived
separately so untangling them means unpicking two synced spec sets. When the
grouping is genuinely ambiguous, merge. If you find yourself proposing more than
five slices for one working tree, the grouping is too fine — merge related slices
before continuing.

Give each slice a kebab-case change name that describes its behavior
(`add-payment-retry`, not `update-payment-files`).

### 4. Order the slices

Archive order is a correctness constraint, not a preference:

- A slice that **adds** a capability precedes any slice that **modifies** it.
- Otherwise, order is stable by first-touched path.

Slices are processed **strictly sequentially, never in parallel**. Archiving
syncs delta specs into `openspec/specs/<capability>/spec.md`; two slices touching
one capability at the same time would race on the same file and the loser's
requirements would vanish.

### 5. Per slice — author, check, archive

For each slice in order, run 5a → 5b → 5c to completion before starting the next
slice. Dispatch every subagent **synchronously** (`run_in_background: false`) and
give it the scratchpad paths, the slice's file list, the change name, and the
`INTENT_HINT`.

#### 5a. Author the artifacts (spec model)

Dispatch a subagent with `model` = the **spec** model. It creates the change and
writes the artifacts:

```bash
openspec new change "<slice-name>"
openspec status --change "<slice-name>" --json     # artifact graph + build order
openspec instructions <artifact> --change "<slice-name>" --json
```

Follow the CLI's `template` and `instruction` for each artifact, in dependency
order (proposal → specs and design → tasks), exactly as `openspec-propose` does —
`context` and `rules` are constraints on the author, never content copied into
the file.

Do **not** delegate this to the `openspec-propose` skill. Propose authors from a
description and leaves tasks unchecked; this phase authors from a diff and must
leave every task checked. Post-editing propose's output into that shape is more
work than writing it correctly once, and it invites artifacts that describe the
imagined change rather than the real one.

Then add `reconciled: true` and `reconciled_from: <working-tree | ref-range>` to
the change's `.openspec.yaml`. The CLI tolerates the extra keys, and they are the
only durable record that this change was written after its code.

The content rules are in **Authoring rules** below. They are not optional.

#### 5b. Coverage check (check model)

Dispatch a **separate** subagent with `model` = the **check** model. Give it only
the slice's diff hunks and the artifacts just written — not the author's
reasoning, not this skill's narrative. An author checking its own artifacts
grades its reading of the diff against itself and passes every time; the whole
value of this phase is that it has not already decided what the diff means.

It reports PASS or FAIL against four questions:

1. **Hunk coverage** — is every hunk in the slice accounted for by at least one
   task? Name any that are not.
2. **Task grounding** — does every task correspond to something actually in the
   diff? Name any task that describes work not present.
3. **Requirement truth** — does every requirement and scenario describe behavior
   the changed code actually has? Name any that overstate, generalize beyond the
   code, or describe an intended future state.
4. **Deletion coverage** — does the diff remove behavior that a live requirement
   in `openspec/specs/` still asserts, without a corresponding `## REMOVED
   Requirements` entry? This is the failure that a reconciliation is most likely
   to miss, because adding is easy and retiring is invisible.

On FAIL, re-dispatch **5a** once with the findings appended, then re-check. If
the second check also fails, **stop and report** with the outstanding findings.
Archive nothing. Do not resolve a coverage failure by editing code so it matches
the artifacts.

#### 5c. Archive and sync (archive model)

Dispatch a subagent with `model` = the **archive** model, instructing it to
invoke `openspec-archive-change` autonomously with the explicit slice name. Every
task is already `- [x]` and every artifact is complete, so its completion prompts
are satisfied; it takes the recommended **delta-spec sync** default ("Sync now").

**Then verify the sync actually landed.** For each capability in the slice's
`specs/`, confirm the requirements now appear in
`openspec/specs/<capability>/spec.md`, and that a `## REMOVED Requirements` entry
actually removed them. Do not take the subagent's word for it. The sync path
inside `openspec-archive-change` delegates to an `openspec-sync-specs` skill that
is **not installed in every environment**; where it is missing, the archive can
complete with the change moved but the live specs untouched, which leaves the
spec set silently stale — the exact failure this skill exists to repair.

If the deltas did not land, run the CLI, which archives and updates main specs in
one step:

```bash
openspec archive -y "<slice-name>"
```

The synced specs become the live spec set that the next change reads, so they
must reflect what the code actually does.

### 6. Verify nothing outside `openspec/` moved

Recompute the fingerprint exactly as in step 1 and compare:

```bash
{ git diff HEAD -- . ':(exclude)openspec';
  git ls-files --others --exclude-standard -- . ':(exclude)openspec'; } \
  | shasum
```

A mismatch means a phase edited the code it was supposed to be documenting.
**Stop and report it as a failure**, naming the files that changed
(`git status --porcelain`) so the caller can revert them. Do not attempt to
repair it by editing further.

### 7. Report

Print the output block below. Do not commit.

## Authoring rules

The artifacts must read as though they were written **before** the code, because
that is what makes them usable as a spec record. That is a rule about voice, not
a licence to invent: everything asserted must be true of the diff.

**`proposal.md`**

- **Why** — the motivation. Reconstruct it from the `INTENT_HINT` first, then
  commit messages, branch name, `docs/roadmaps/`, existing specs, and the shape
  of the code itself. Where the motivation genuinely cannot be recovered, write
  the narrowest rationale the diff supports ("callers had no way to retry a
  failed charge") and list it in the report's **Inferences**. Never invent a
  business justification, a metric, an incident, or a stakeholder.
- **What Changes** — the behavioral change, specific and complete.
- **Capabilities** — new vs. modified, matching the delta specs exactly.
- **Impact** — the real files, APIs, and dependencies the diff touches.

**`specs/<capability>/spec.md`** — the delta. For each capability:

- behavior belonging to an existing capability → `## MODIFIED Requirements`, each
  requirement restated in **full new text** (sync consumes the whole requirement,
  not a description of the edit), or `## ADDED Requirements` for genuinely new
  requirements inside it;
- behavior with no existing home → a new capability directory under
  `## ADDED Requirements`;
- behavior the diff **removes** that a live requirement still asserts →
  `## REMOVED Requirements`.

Requirements are `SHALL` statements about behavior present in the tree right now.
Each carries `#### Scenario:` blocks whose `**WHEN**` / `**THEN**` / `**AND**`
bullets are checkable against the changed files by someone holding only the diff.

**`design.md`** — the decisions the code visibly embodies, and their rationale.
Where the code shows a choice was made (a retry budget of 3, a lookup table over
a switch), state the decision and the tradeoff it settles. Do not describe
alternatives the author never considered as though they were weighed. Non-Goals
are what the diff conspicuously does not do.

**`tasks.md`** — the instructions that *would have* produced these hunks, grouped
the way the work would have been sequenced, **every box `- [x]`**. Each task
names what it changed and carries a verify clause pointing at what is actually in
the tree. A task nobody could check against the diff is a task that should not be
there.

**No hedging in the artifacts.** No "we inferred", "this appears to", "presumably
the author". The provenance lives in `.openspec.yaml` and in the report's
**Inferences** list — those two places, honestly and completely, so the artifacts
can stay readable as what they claim to be.

## Output

```
## OpenSpec reconciliation complete

**Source:** working tree (uncommitted) | <ref-range>
**Slices:** <n>  (or: 1, --single)
**Models:** spec=<model> check=<model> gate=<model> archive=<model>

### Gate
- <passed | environment-blocked: reason | no gate defined>

### Changes archived
1. <change-name> → openspec/changes/archive/YYYY-MM-DD-<change-name>/
   - Files: <path>, <path>
   - Capabilities: <cap> (+N added, ~N modified, -N removed)
2. ...

### Inferences
- <motivation reconstructed rather than read, and what it was reconstructed from>
- <"why" that could not be recovered, and the narrow rationale written instead>

### Not reconciled
- <openspec/ paths already modified in the source diff, or files deliberately excluded>

Code untouched: verified — nothing outside openspec/ changed.
Working tree left uncommitted. Undo everything with:
  git checkout -- openspec/ && git clean -fd openspec/
```

## Guardrails

- **Never edit code.** Only `openspec/` is writable. Step 6 enforces it; a
  mismatch is a failed run, not a warning.
- **Never archive a slice that failed its coverage check** after one retry, and
  never archive anything at all after a genuine gate failure.
- **Never fabricate motivation.** An unrecoverable "why" gets the narrowest
  rationale the diff supports plus an entry in **Inferences** — never an invented
  incident, metric, deadline, or stakeholder.
- **Never let the artifacts outrun the diff.** A requirement that generalizes
  beyond what the code does is a false record that the next change will build on.
- **Never trust an unverified sync.** Confirm the deltas reached
  `openspec/specs/` before moving to the next slice; an archive that moved the
  directory without updating the live specs looks like success and is not.
- **Never process slices in parallel.** Delta sync writes shared spec files.
- **Never re-derive the diff mid-run.** Read the step 1 snapshot.
- **Never commit, branch, push, or merge.** The run ends with an uncommitted
  tree.
- **Reject malformed model tokens** before any phase is dispatched.

## Red flags — stop and reconsider

- "This requirement would be cleaner if I just renamed that function."
- "The coverage check failed, but I could make it pass by tweaking the code."
- "The gate failure is probably pre-existing — I'll stash and check."
- "I'll fix this obvious bug while I'm in here; it's one line."
- "I don't know why they did this, but a plausible reason would be…"
- "These files are unrelated enough to be their own slice" (for the fourth time).
- "The spec should describe where this is heading, not just where it is."

**Each of these means: leave the code alone and write down what is actually
there.**

| Rationalization | Reality |
|---|---|
| "The code is obviously wrong; documenting it enshrines the bug." | The record's job is to be true. Report the bug in the report; the caller decides. A spec that describes code nobody wrote is worse than one describing imperfect code. |
| "Editing one line makes the spec much cleaner." | Then the spec no longer describes the diff you were given, and the caller's work has been silently rewritten under cover of a documentation task. |
| "The author checked its own artifacts, so a second model is wasted tokens." | An author grades its own reading of the diff against itself. The check exists precisely because that comparison always passes. |
| "Six slices is more accurate than three." | Accuracy about file boundaries, at the cost of fabricating six histories. Merge. |
| "No `REMOVED` section is needed — nothing was deleted." | Deleted *behavior* is not deleted *lines*. Check what the live requirements still assert. |
| "I'll infer the business reason; it's clearly about performance." | Clearly to you, from a diff. Write what the code supports and list the inference. |
| "Tasks were never really done in this order, so the grouping is fiction." | Task grouping is a reading of the work, not a claim about chronology. Fabricating *content* is the line, not sequencing. |
