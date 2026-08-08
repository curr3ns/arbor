## ADDED Requirements

### Requirement: The skill documents two modes and defaults to one cycle per invocation

`.claude/skills/arbor-auto-developer/SKILL.md` SHALL document exactly two modes and SHALL make the contrast between them legible near the top of the file rather than presenting `--goal` as one entry in a list of options. The **default, scheduled mode** — invoked with no `--goal` — SHALL remain exactly what it is today: unattended, cron-paced, one cycle per invocation, exiting when the item is handled or the walk finds nothing eligible. The **foreground goal mode** — invoked with `--goal` — SHALL be described as human-invoked and running until a stated finish line. The mode framing SHALL state the default in the same place it names the flag, so that the one-cycle default is visible where an agent forms its plan and not only in the guardrails.

#### Scenario: Default remains one cycle

- **WHEN** the skill is invoked without `--goal`
- **THEN** it works exactly one item per invocation and then exits
- **AND** it does not loop internally
- **AND** nothing about the scheduled path's behavior differs from what it was before this change

#### Scenario: The mode contrast is stated near the top

- **WHEN** the opening framing of the skill is read
- **THEN** it names both the default scheduled mode and the `--goal` foreground mode
- **AND** it states that without `--goal` the skill runs one cycle per invocation
- **AND** the contrast is drawn on who invokes the mode and what ends the run, not merely on the presence of a flag

#### Scenario: The flag is not buried in an options list

- **WHEN** the finished skill is read
- **THEN** `--goal` has its own section carrying its behavior
- **AND** its behavior is not specified solely as a bullet among other invocation options

### Requirement: `--goal` sets a session-scoped goal naming the target roadmap

When invoked with `--goal`, the skill SHALL set a goal via `/goal` whose condition names the target roadmap, literally of the form:

> Every item in `docs/roadmaps/<slug>.md` is checked off and the file has been migrated to `docs/roadmaps/archive/`

with `<slug>` substituted for the target roadmap's actual slug. The skill SHALL document that `/goal` installs a **session-scoped Stop hook**, which is what keeps the session going between items and what auto-clears when the condition holds. The condition SHALL name exactly one roadmap and SHALL retain the archival clause, because a completed roadmap has been `git mv`d out of `docs/roadmaps/` by `arbor-auto-work` and a condition phrased only in terms of the original path would be evaluated against a file that no longer exists. The skill SHALL set the goal once, at the start of the run, and SHALL NOT re-issue it with a different condition mid-session.

#### Scenario: The condition names the roadmap

- **WHEN** the goal-mode section is read
- **THEN** the condition it sets is of the form "Every item in `docs/roadmaps/<slug>.md` is checked off and the file has been migrated to `docs/roadmaps/archive/`"
- **AND** `<slug>` is described as the target roadmap's actual slug rather than left as a literal

#### Scenario: The Stop hook mechanism is documented

- **WHEN** the goal-mode section is read
- **THEN** it states that `/goal` sets a session-scoped Stop hook
- **AND** it states that the hook is what keeps the session going between items
- **AND** it states that the hook auto-clears when the condition holds

#### Scenario: The condition is not open-ended

- **WHEN** the condition the skill sets is read
- **THEN** it is a factual statement about one named roadmap file
- **AND** it is not an open-ended instruction such as "keep working until the roadmaps are done"

#### Scenario: The goal is set once

- **WHEN** a goal run is under way
- **THEN** the skill does not re-issue `/goal` with a different condition
- **AND** the roadmap the condition names does not change during the run

### Requirement: The goal run's target roadmap is chosen deterministically and pinned

The skill SHALL document how the target roadmap is chosen. When the human names a roadmap as an argument to `--goal` — as a slug or as a `docs/roadmaps/<slug>.md` path — that roadmap SHALL be the target; when the named roadmap does not exist among the non-archived roadmaps, the run SHALL stop and report rather than silently selecting a different one. When no argument is given, the target SHALL be the **first roadmap holding an eligible item** under the skill's existing filename-order walk. The target SHALL be resolved once, at the start of the run, and SHALL be pinned for the rest of the run rather than re-derived each iteration. When the session resumes after a Stop-hook re-prompt, the skill SHALL recover its target from `/goal active` rather than re-running the walk.

#### Scenario: A named roadmap is the target

- **WHEN** `--goal` is invoked with a roadmap slug or path
- **THEN** that roadmap is the target and its slug is what appears in the `/goal` condition

#### Scenario: A named roadmap that does not exist stops the run

- **WHEN** `--goal` names a roadmap that is not present among the non-archived `docs/roadmaps/*.md`
- **THEN** the run stops and reports that the named roadmap was not found
- **AND** no goal is set
- **AND** a different roadmap is not selected in its place

#### Scenario: With no argument the existing walk chooses the target

- **WHEN** `--goal` is invoked with no roadmap argument
- **THEN** the target is the first roadmap holding an eligible item by the skill's existing filename-order walk
- **AND** no new selection rule is introduced for this case

#### Scenario: The target is pinned, not re-derived

- **WHEN** a goal run continues to its next item
- **THEN** it works the same roadmap the `/goal` condition names
- **AND** it does not re-run the first-eligible walk to pick a possibly different roadmap
- **AND** on resuming after a Stop-hook re-prompt it recovers the target from `/goal active`

#### Scenario: Nothing eligible anywhere means no goal is set

- **WHEN** `--goal` is invoked and no non-archived roadmap holds an eligible item
- **THEN** no goal is set
- **AND** the skill reports and exits on the same quiet path a scheduled idle tick takes

#### Scenario: A named but ineligible roadmap means no goal is set

- **WHEN** `--goal` names a roadmap that exists but holds no eligible item
- **THEN** no goal is set
- **AND** the skill reports why and exits

### Requirement: The goal run works items one at a time with one subagent in flight

The goal run SHALL work items **one at a time** — the same single dispatch per cycle the default mode performs, repeated. Exactly one subagent SHALL be in flight at any moment across the entire goal run, retries included; the skill SHALL NOT dispatch two subagents concurrently and SHALL NOT batch, queue, or pre-select multiple items. Each cycle SHALL complete fully — dispatch, verification, notification or annotation — before the next cycle begins, and each cycle SHALL re-read the queue from `main` so that the previous cycle's merge or annotation is visible to the next cycle's walk. Dispatch SHALL remain autonomous: `--goal` describes a human watching the session, not approval prompts, so subagents still run `arbor-auto-work` in its default mode with no `--interaction` and no `--pr`.

#### Scenario: One subagent at a time across the whole run

- **WHEN** the goal-mode section is read
- **THEN** it states that exactly one subagent is in flight at any moment for the entire run
- **AND** it states that a retry follows a finished attempt rather than overlapping it
- **AND** nothing directs batching or concurrent dispatch

#### Scenario: Each cycle finishes before the next begins

- **WHEN** an item's cycle has been dispatched
- **THEN** the run does not begin the next item's cycle until that cycle has completed
- **AND** the next cycle re-reads the roadmap queue on `main`

#### Scenario: Dispatch stays autonomous in goal mode

- **WHEN** the goal-mode section's dispatch behavior is read
- **THEN** subagents run `arbor-auto-work` in its default autonomous mode
- **AND** neither `--interaction` nor `--pr` is passed
- **AND** "foreground" is explained as the human watching the session rather than as interactive approval

#### Scenario: Under `/goal` the repetition belongs to the hook

- **WHEN** the `/goal` path is read
- **THEN** the skill runs one cycle per turn and then stops, and the Stop hook brings the session back
- **AND** the skill does not additionally loop internally while a Stop hook is driving the session

### Requirement: Both the goal path and the fallback terminate on the same condition and cannot livelock

Both the `/goal` path and the fallback path SHALL terminate on the same condition: **no eligible item remains in the target roadmap** — either because the roadmap is finished and has been archived, or because every unchecked item that remains carries a `<!-- blocked: ... -->` annotation. An all-blocked roadmap SHALL be treated as a **terminating state, not a retry state**: the skill SHALL NOT re-attempt blocked items to keep the loop alive, and SHALL NOT invent a triage pass over them.

The skill SHALL state why the loop cannot livelock: every iteration either merges the item, leaving the roadmap one unchecked item shorter, or exhausts the item's two attempts and annotates it blocked, leaving the roadmap one *eligible* item shorter; both quantities strictly decrease over a finite item set, so the loop reaches "no eligible item" in a bounded number of iterations. The goal run SHALL additionally keep a session-local record of items it has exhausted during the run and treat them as ineligible for the remainder of the run, so that termination does not depend on the blocked-annotation push having landed.

#### Scenario: An all-blocked target roadmap terminates the run

- **WHEN** the target roadmap still has unchecked items but every one of them carries a `<!-- blocked: ... -->` annotation
- **THEN** the run terminates
- **AND** the skill does not re-attempt any blocked item
- **AND** the skill does not describe a triage or re-attempt pass over blocked items

#### Scenario: The termination argument is written down

- **WHEN** the goal-mode section is read
- **THEN** it states that each iteration either merges an item or blocks one
- **AND** it states that both outcomes strictly reduce the number of eligible items
- **AND** it states that the loop therefore terminates rather than leaving the reader to infer it

#### Scenario: The fallback terminates identically

- **WHEN** the fallback path runs cycles back-to-back in-session
- **THEN** it stops when no eligible item remains in the target roadmap
- **AND** its stopping condition is the same one the `/goal` path uses, not a separate rule

#### Scenario: Exhausted items are ineligible for the rest of the run

- **WHEN** an item has used both of its attempts during a goal run
- **THEN** the run does not select that item again for the remainder of the run
- **AND** this holds whether or not the blocked annotation was successfully pushed to `main`

### Requirement: The skill clears the goal when the loop terminates without the condition holding

When the loop terminates because the target roadmap holds no eligible item but the condition has **not** been satisfied — the all-blocked case, or any other case where the roadmap is neither finished nor archived — the skill SHALL issue `/goal clear` itself before stopping, and SHALL report which items are blocked and why. The skill SHALL state the reason: the condition can never become true in that state, so a Stop hook left active would keep re-prompting a session that has correctly concluded there is nothing left to do. When the condition **does** hold, the skill SHALL rely on the hook's own auto-clear and SHALL NOT be required to clear it manually.

#### Scenario: All-blocked termination clears the goal

- **WHEN** the goal run terminates because every remaining unchecked item in the target roadmap is blocked-annotated
- **THEN** the skill issues `/goal clear`
- **AND** it reports the blocked items and their reasons
- **AND** it does not leave an active Stop hook behind

#### Scenario: The reason for clearing is stated

- **WHEN** the `/goal clear` instruction is read
- **THEN** it states that the condition can never hold in that state
- **AND** it states that an active Stop hook would otherwise keep re-prompting a finished session

#### Scenario: A satisfied condition needs no manual clear

- **WHEN** the target roadmap is completed and archived
- **THEN** the condition holds and the hook auto-clears
- **AND** the skill is not required to issue `/goal clear` in that case

### Requirement: The two-attempt budget is per item and "don't move on" is a within-cycle rule

The skill SHALL state the operative reading of its existing per-run budget under a loop that spans many items. The budget of **at most two attempts — one original plus one retry — SHALL be per item**, and an item that exhausts it is annotated blocked and thereafter skipped by the walk, so no item receives a third attempt within a goal run either. The companion rule that the cycle never moves on to a different item in place of a failed one SHALL be stated as a **within-cycle** rule: a failed cycle never chains into another item, and the goal run reaches the next item by starting a new cycle whose walk re-reads `main`, not by continuing a failed one. Neither rule SHALL be softened, and the scheduled path's behavior SHALL be unchanged by this clarification.

#### Scenario: The budget is scoped to the item

- **WHEN** the attempt-budget guardrail is read
- **THEN** it states that at most two attempts are made on the same item
- **AND** it states that an item that exhausts the budget is annotated and thereafter skipped
- **AND** it does not permit a third attempt on the same item anywhere in a goal run

#### Scenario: The goal run advances by starting a new cycle

- **WHEN** an item is blocked during a goal run
- **THEN** the failed cycle ends without picking a replacement item
- **AND** the run advances to the next item by beginning a new cycle that re-reads the queue on `main`
- **AND** the distinction between chaining within a cycle and starting a new cycle is stated rather than implied

#### Scenario: The scheduled path is unaffected by the clarification

- **WHEN** the clarified rules are read against a scheduled invocation with no `--goal`
- **THEN** each remains true word for word
- **AND** the scheduled run still handles exactly one item and exits

### Requirement: `/goal` availability is documented and unavailability falls back with the reason reported

The skill SHALL document that `/goal` **requires a trusted workspace and unrestricted hooks**. It SHALL state that `/goal` is unavailable when `disableAllHooks` or `allowManagedHooksOnly` is set — both named individually — and SHALL note that Stop hooks are REPL-only, so a non-REPL invocation cannot have one either. When `/goal` is unavailable for any of these reasons, the skill SHALL **report the reason** and SHALL **fall back to running cycles back-to-back in-session** until no eligible item remains in the target roadmap. The unavailability SHALL NOT abort the run, and the report SHALL be prose in the session rather than a `PushNotification`.

#### Scenario: The two preconditions are stated

- **WHEN** the goal-mode section is read
- **THEN** it states that `/goal` requires a trusted workspace
- **AND** it states that `/goal` requires unrestricted hooks

#### Scenario: Both restricted-hooks settings are named

- **WHEN** `grep -n 'disableAllHooks' .claude/skills/arbor-auto-developer/SKILL.md` and `grep -n 'allowManagedHooksOnly' .claude/skills/arbor-auto-developer/SKILL.md` are run
- **THEN** each matches
- **AND** both appear as named causes of `/goal` being unavailable

#### Scenario: The REPL-only limitation is captured

- **WHEN** the goal-mode section is read
- **THEN** it notes that Stop hooks are REPL-only
- **AND** it presents that as a further legitimate reason the fallback path exists

#### Scenario: Unavailability reports and falls back rather than aborting

- **WHEN** `/goal` cannot be set
- **THEN** the skill reports which of the reasons applied
- **AND** it proceeds to run cycles back-to-back in-session until no eligible item remains
- **AND** the run is not aborted

#### Scenario: The fallback is the same cycles, repeated

- **WHEN** the fallback path is read
- **THEN** it is described as the same single-item cycle run back-to-back in-session
- **AND** it is not a second, differently-specified algorithm

### Requirement: A goal run targets one roadmap and hands off when others remain

A goal run SHALL finish one roadmap. When the target roadmap completes while other non-archived roadmaps still hold eligible items, the run SHALL end with the condition met and SHALL report the roadmaps that still hold eligible work together with the invocation that would continue with the next one. The skill SHALL NOT roll onto another roadmap within the same goal run.

#### Scenario: The run ends when its named roadmap completes

- **WHEN** the target roadmap's last item merges and the file is archived
- **THEN** the condition holds and the run ends
- **AND** the skill does not begin working a different roadmap in the same run

#### Scenario: Remaining roadmaps are reported

- **WHEN** the run ends and other non-archived roadmaps still hold eligible items
- **THEN** the skill reports which roadmaps still hold eligible work
- **AND** it names the invocation that would continue with the next one

### Requirement: The goal mode adds no notification event and no new behavior to the settled contracts

The goal mode SHALL NOT add a fourth notification trigger. The existing three — merge landed, item blocked after retry, roadmap complete — SHALL fire per cycle exactly as already specified, and SHALL be the only triggers in the file. Neither setting a goal nor reaching one SHALL be a notification event. The goal mode SHALL NOT rewrite, soften, or contradict the settled behavior established for this skill: the roadmap-queue walk and its archive exclusion, the phases-are-strictly-sequential rule, the selection of exactly one item per cycle, the dispatch contract and its `{ outcome, work_id, branch, note }` return, the retry-then-blocked-annotation path with its push race and its abandonment rule, the roadmap-completion observation, the merge-to-`main` target, and the never-author-roadmap-content guardrails all SHALL survive unchanged in force.

#### Scenario: Still exactly three notification triggers

- **WHEN** the notifications section of the finished skill is read
- **THEN** it enumerates merge landed, item blocked after retry, and roadmap complete
- **AND** it lists no fourth trigger anywhere in the file
- **AND** neither "goal set" nor "goal reached" is a notification event

#### Scenario: Settled behavior is untouched

- **WHEN** the roadmap walk, the strictly-sequential phase rule, the dispatch section, the annotation path and its push race, the completion observation, and the guardrails are read in the finished file
- **THEN** each states the same rule with the same force as before this change
- **AND** the only changes to them are scope qualifiers that name `--goal` as the condition under which repetition is permitted

#### Scenario: The one-cycle guardrail is scoped, not weakened

- **WHEN** the guardrail that one run is one cycle with no internal loop is read
- **THEN** it is scoped to the default, scheduled invocation rather than softened into a preference
- **AND** it remains true word for word of any invocation that does not pass `--goal`

### Requirement: Frontmatter mentions the mode and the version is bumped

The YAML frontmatter `description` SHALL mention the new foreground `--goal` mode, while continuing to describe the default scheduled, one-cycle-per-run behavior. `metadata.version` SHALL be bumped from `"2.0"`, and the frontmatter SHALL still parse as YAML with `name`, `description`, `license`, and `metadata` present.

#### Scenario: The description mentions the mode

- **WHEN** the frontmatter `description` is read
- **THEN** it mentions the `--goal` foreground mode
- **AND** it still states that the default is a scheduled run of a single cycle, not a loop

#### Scenario: Description matches the body

- **WHEN** the frontmatter `description` is read against the body
- **THEN** every behavior it claims is one the body specifies
- **AND** it claims no behavior the body does not specify

#### Scenario: Version is bumped from 2.0

- **WHEN** `grep -n 'version:' .claude/skills/arbor-auto-developer/SKILL.md` is run
- **THEN** the value is no longer `"2.0"`
- **AND** the frontmatter still parses with `name`, `description`, `license`, and `metadata` present

## MODIFIED Requirements

### Requirement: Change scope is limited to the auto-developer skill

Implementing this change SHALL modify only `.claude/skills/arbor-auto-developer/SKILL.md` and the OpenSpec artifacts for this change. The skills `arbor-auto-work`, `arbor-auto-roadmap`, `arbor-opsx-auto`, and `arbor-project-scaffold` SHALL NOT be created, modified, moved, or deleted, and no new skill directory SHALL be added. No `docs/roadmaps/archive/` directory, placeholder, or `.gitkeep` SHALL be created or committed by this change. `docs/roadmaps/roadmap-native-workcycles.md` SHALL be read for context and SHALL NOT be modified — R5's own checkbox is flipped outside this change, by `arbor-auto-work`'s commit step. The edit to `arbor-auto-developer` SHALL be additive: beyond the frontmatter `description` and `metadata.version`, the only permitted changes to existing prose are the scope qualifiers that name `--goal` as the condition under which repetition is permitted.

#### Scenario: No other path is touched

- **WHEN** `git status --porcelain` is inspected after implementation
- **THEN** the only path listed outside `openspec/` is a modification to `.claude/skills/arbor-auto-developer/SKILL.md`
- **AND** no path under `.claude/skills/arbor-auto-work/`, `.claude/skills/arbor-auto-roadmap/`, `.claude/skills/arbor-opsx-auto/`, or `.claude/skills/arbor-project-scaffold/` appears
- **AND** no new skill directory exists

#### Scenario: The archive directory is not materialized here

- **WHEN** the working tree is inspected after implementation
- **THEN** `docs/roadmaps/archive/` has not been created or committed

#### Scenario: The parent roadmap file is left alone

- **WHEN** `git status --porcelain` is inspected
- **THEN** `docs/roadmaps/roadmap-native-workcycles.md` does not appear

#### Scenario: The edit is additive

- **WHEN** `git diff` of `.claude/skills/arbor-auto-developer/SKILL.md` is read
- **THEN** every change is either an addition, the frontmatter `description` and version update, or a scope qualifier naming `--goal`
- **AND** no settled rule from the walk, the dispatch section, the annotation path, the notifications, or the guardrails is rewritten or softened
