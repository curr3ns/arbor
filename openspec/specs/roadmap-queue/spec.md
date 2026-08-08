## ADDED Requirements

### Requirement: The issue backlog and every artifact of it are removed

`.claude/skills/arbor-auto-developer/SKILL.md` SHALL contain no `agent:backlog` queue, no label requirement of any kind (including `priority:*` and `type:*`), no queue cap, no `gh auth` setup step, no integration-branch setup step, no running pull request, no "at most one open PR" guardrail, no P0/P1 pull-request-feedback path, and no refine self-seeding. Every one of these SHALL be deleted outright rather than softened, made conditional, or retained as a commented-out or optional branch. The skill SHALL contain zero occurrences of the string `arbor-auto-refine`, in the YAML frontmatter description and in the body alike. Every removal SHALL be a considered rewrite rather than a deletion in place: the surrounding prose SHALL read naturally and completely, with no stub sentence, dangling conjunction, orphaned parenthetical, or claim left without its subject.

#### Scenario: No refine reference survives

- **WHEN** `grep -n 'arbor-auto-refine' .claude/skills/arbor-auto-developer/SKILL.md` is run
- **THEN** it produces no output and exits non-zero

#### Scenario: No backlog, label, or cap machinery survives

- **WHEN** the finished skill is searched for `agent:backlog`, `priority:`, `type:`, and any statement of a maximum number of queued items
- **THEN** none of them appears
- **AND** nothing in the file directs listing, filtering, sorting, labelling, commenting on, or closing a GitHub issue

#### Scenario: No pull-request path survives

- **WHEN** the finished skill is searched for `gh pr`, `pull request`, `review comment`, `review thread`, `CHANGES_REQUESTED`, and `integration branch`
- **THEN** none of them appears
- **AND** there is no step that polls for feedback, no P0/P1 priority scheme, and no instruction to reply to or resolve a review thread
- **AND** the single permitted occurrence of the string `--pr` is the dispatch section's statement that the flag is **not** passed, which is required by the dispatch requirement below and is not a pull-request path

#### Scenario: Removals leave no scar

- **WHEN** each part of the file that previously depended on the backlog, the running PR, or refine is read in its final form
- **THEN** it is a complete, grammatical statement that stands on its own
- **AND** it contains no empty slot, trailing "and", or dangling "(agent 2)"-style label where removed content used to be

### Requirement: Each cycle reads non-archived roadmaps on main as its queue

Each cycle SHALL read the non-archived roadmap files `docs/roadmaps/*.md` as it stands on `main`, and SHALL NOT read `docs/roadmaps/archive/`. The exclusion of the archive directory SHALL be stated explicitly rather than left implied by the shape of the glob, so that a recursive search does not resurrect completed roadmaps as work.

#### Scenario: Archive directory is excluded by name

- **WHEN** the step that reads the queue is read
- **THEN** it names `docs/roadmaps/*.md` as the queue
- **AND** it states that `docs/roadmaps/archive/` is excluded

#### Scenario: The read is against main

- **WHEN** the step that reads the queue is read
- **THEN** it states that the roadmaps are read as they stand on `main`, not on whatever branch happens to be checked out

#### Scenario: Completed roadmaps are never re-selected

- **WHEN** a roadmap has been archived by a previous cycle and now lives at `docs/roadmaps/archive/<slug>.md`
- **THEN** the cycle does not consider any of its items
- **AND** it is not treated as a source of eligible work

### Requirement: Selection walks roadmaps in filename order and picks one item

The cycle SHALL walk the non-archived roadmap files in filename order. Within the first roadmap that holds an eligible item, it SHALL take the earliest incomplete phase and, within that phase, the first unchecked item that does not carry a blocked annotation. A phase SHALL be treated as incomplete when at least one item under it is unchecked, whether or not that item carries a blocked annotation. Exactly one item SHALL be selected per cycle.

#### Scenario: Ordinary selection

- **WHEN** the first roadmap in filename order has an unchecked, unannotated item in its earliest incomplete phase
- **THEN** that item is selected
- **AND** no item from any later roadmap, later phase, or later position in the phase is considered

#### Scenario: Filename order is the outer key

- **WHEN** two or more non-archived roadmap files hold eligible items
- **THEN** the walk considers them in filename order and selects from the first one that holds an eligible item

#### Scenario: A checked item is skipped

- **WHEN** the earliest incomplete phase's first item is already `- [x] **R<n>**`
- **THEN** it is skipped and the next unchecked, unannotated item in that phase is considered

### Requirement: An all-blocked roadmap yields nothing and the walk continues

When every unchecked item in a roadmap carries a blocked annotation, that roadmap SHALL be treated as holding no eligible item, and the walk SHALL move on to the next roadmap in filename order rather than idling. This SHALL be stated explicitly in the skill.

#### Scenario: Walk moves past an all-blocked roadmap

- **WHEN** the first roadmap in filename order has unchecked items but every one of them carries a `<!-- blocked: ... -->` annotation
- **THEN** the cycle selects nothing from that roadmap
- **AND** it continues the walk to the next roadmap file by filename
- **AND** it does not end the run merely because the first file yielded nothing

#### Scenario: A later roadmap still supplies work

- **WHEN** an earlier roadmap is entirely blocked and a later roadmap has an eligible item
- **THEN** the later roadmap's item is selected and dispatched

### Requirement: A blocked earliest phase does not fall through to a later phase

When the earliest incomplete phase of a roadmap has unchecked items but all of them carry a blocked annotation, the cycle SHALL NOT select an item from a later phase of that same roadmap. Phases are strictly sequential. That roadmap SHALL yield nothing and the walk SHALL continue to the next roadmap file in filename order. This SHALL be stated explicitly in the skill, in terms that forbid the fall-through rather than merely omitting it.

#### Scenario: No fall-through within a roadmap

- **WHEN** Phase 1 of a roadmap has one unchecked item and that item carries a blocked annotation, while Phase 2 has several unchecked, unannotated items
- **THEN** no Phase 2 item is selected
- **AND** the roadmap yields nothing this cycle
- **AND** the walk continues to the next roadmap file

#### Scenario: A blocked item keeps its phase incomplete

- **WHEN** the only unchecked item in a phase carries a blocked annotation
- **THEN** that phase is still treated as incomplete
- **AND** later phases in the same roadmap remain ineligible

#### Scenario: The rule is stated, not implied

- **WHEN** the selection step and the guardrails are read
- **THEN** the skill states that a later phase is never worked while an earlier phase still holds an unchecked item
- **AND** it states that a fully blocked earliest phase does not open a later phase

### Requirement: Exactly one subagent per cycle runs arbor-auto-work autonomously against main

For the selected item the cycle SHALL dispatch exactly one subagent with a self-contained prompt, and SHALL wait for it to finish before doing anything else. The prompt SHALL instruct the subagent to run the `arbor-auto-work` skill in autonomous mode — its default, with no `--interaction` and no `--pr` — carrying the item's full text and the item's reference in the form `roadmap:docs/roadmaps/<slug>.md#R<n>`, and merging to `main`. The skill SHALL NOT instruct the subagent to override the integration target, because `main` is already `arbor-auto-work`'s default. The dispatch section SHALL state that the subagent returns the compact result `{ outcome, work_id, branch, note }`.

#### Scenario: Dispatch carries the item and its reference

- **WHEN** the dispatch section is read
- **THEN** it directs passing the selected item's full text and the `roadmap:docs/roadmaps/<slug>.md#R<n>` reference for that item
- **AND** the reference format matches the format `arbor-auto-roadmap` defines

#### Scenario: Autonomous mode with no flags

- **WHEN** the dispatch section is read
- **THEN** it names autonomous mode as `arbor-auto-work`'s default
- **AND** it states that neither `--interaction` nor `--pr` is passed

#### Scenario: Merge target is main with no override

- **WHEN** the dispatch section is read
- **THEN** the merge target is `main`
- **AND** no instruction directs the subagent to branch off or merge into anything other than `main`

#### Scenario: Return contract is stated

- **WHEN** the dispatch section is read
- **THEN** it states that the subagent returns `{ outcome, work_id, branch, note }`

#### Scenario: One subagent, sequentially

- **WHEN** a cycle runs
- **THEN** at most one subagent is in flight at any moment
- **AND** a retry subagent is dispatched only after the first has finished

### Requirement: No eligible item and no roadmap at all both end the run quietly

When the walk finds no eligible item in any roadmap, the run SHALL end immediately with no dispatch, no notification, and no error. The same SHALL hold when no roadmap file exists at all: the absence of `docs/roadmaps/*.md` SHALL NOT be treated as a setup failure, a misconfiguration, or an error condition. In both cases there is nothing to do until the next scheduled tick.

#### Scenario: Nothing eligible

- **WHEN** every non-archived roadmap is fully checked, or every unchecked item is blocked, or every roadmap's earliest incomplete phase is fully blocked
- **THEN** the run ends without dispatching a subagent
- **AND** no notification is sent
- **AND** no error is raised

#### Scenario: No roadmap files at all

- **WHEN** `docs/roadmaps/` contains no non-archived roadmap file, or does not exist
- **THEN** the run ends quietly in the same way
- **AND** the skill does not report a setup problem, create the directory, or invoke `arbor-auto-roadmap`

### Requirement: One retry on gate failure, and never a third attempt

When the dispatched subagent reports a gate failure, the cycle SHALL dispatch exactly one retry subagent, in a fresh context, passing the failure output. If the retry also fails, the cycle SHALL stop working that item. The skill SHALL NOT make a third attempt on the same item in the same run, and SHALL NOT move on to a different item after a blocked one in the same run.

The skill SHALL handle the returned `outcome` as a total two-way branch, so that no possible value is left without a defined response: `shipped` routes to the success path, and every other value routes to this retry-then-annotate path. This SHALL explicitly cover `failed`, `blocked` — which `arbor-auto-work` can genuinely report, since it stops before committing when a `roadmap:` reference does not resolve — and a missing or unrecognised value.

#### Scenario: Retry carries the failure output

- **WHEN** the first subagent reports a gate failure
- **THEN** exactly one retry subagent is dispatched in a fresh context
- **AND** the failure output is passed to it

#### Scenario: A non-shipped outcome is never left unhandled

- **WHEN** the dispatched subagent returns an `outcome` of `blocked`, or a value the skill does not recognise, rather than `failed`
- **THEN** it is treated as "the merge did not land" and routed to the retry-then-annotate path
- **AND** the skill does not fall through without a defined response

#### Scenario: Two attempts is the ceiling

- **WHEN** the retry subagent also fails
- **THEN** no further subagent is dispatched for that item in that run
- **AND** the cycle does not select a replacement item to work instead

### Requirement: A twice-failed item is annotated as blocked and the annotation is pushed to main

When the retry also fails, the cycle SHALL append an annotation of the form `<!-- blocked: <reason> -->` to the end of the failed item's line and push it to `main` as bookkeeping, so that later cycles skip the item and one bad item cannot stall the roadmap. The annotation SHALL be appended to the end of the item's line, leaving the item's existing text byte-identical, and SHALL NOT reword, reflow, re-wrap, or renumber the item or any of its continuation lines. The `<reason>` SHALL be a one-line summary of what broke at which gate step.

#### Scenario: Annotation form and placement

- **WHEN** an item fails twice in a run
- **THEN** `<!-- blocked: <reason> -->` is appended at the end of that item's line
- **AND** the item's existing text is byte-identical before and after
- **AND** the item's checkbox is left unchecked

#### Scenario: Reason names the failure and the step

- **WHEN** the annotation's reason is written
- **THEN** it is a one-line summary of what broke and at which gate step

#### Scenario: Later cycles skip the annotated item

- **WHEN** a subsequent cycle walks that roadmap
- **THEN** the annotated item is not eligible
- **AND** its phase is still treated as incomplete, so later phases stay closed

#### Scenario: The annotation is pushed, not left local

- **WHEN** the annotation has been applied
- **THEN** it is committed and pushed to `main`
- **AND** it is not left as an uncommitted working-tree change or on a side branch

### Requirement: The blocked-annotation push reconciles with a concurrent change to main

The skill SHALL describe how the annotation push handles a race, because `main` may have moved between the read and the push. On a rejected push the skill SHALL fetch and rebase — or re-pull and re-apply the annotation onto the current `main` — re-locating the item's line by its `**R<n>**` marker rather than by line number, and re-checking that the item is still unchecked and still unannotated before pushing again. If the item has since been checked, or has already been annotated by another actor, the skill SHALL drop the annotation rather than force-push.

#### Scenario: The push is rejected because main moved

- **WHEN** the push of the annotation is rejected because `main` has advanced
- **THEN** the skill fetches and rebases, or re-pulls and re-applies the annotation onto the current `main`
- **AND** it re-locates the item's line by its `**R<n>**` marker, not by line number
- **AND** it re-checks that the item is still unchecked and still unannotated before pushing again

#### Scenario: The item was checked by another actor

- **WHEN** re-checking shows the item is now `- [x] **R<n>**`
- **THEN** the annotation is dropped
- **AND** no force-push is performed

#### Scenario: The item was already annotated by another actor

- **WHEN** re-checking shows the item already carries a blocked annotation
- **THEN** the annotation is dropped rather than duplicated or force-pushed

#### Scenario: Force-push is forbidden

- **WHEN** the annotation-push procedure is read
- **THEN** it forbids force-pushing `main` to make the annotation land

### Requirement: Notifications fire on exactly three events

The skill SHALL send a `PushNotification` — one line, under 200 characters, leading with what is actionable — on exactly three events: a merge landing, an item being blocked after the retry, and a roadmap becoming complete. It SHALL NOT notify on dispatch, and SHALL NOT notify on a quiet idle run. If `PushNotification` is unavailable in the run's environment, the skill SHALL continue without failing the run.

#### Scenario: Exactly three triggers are listed

- **WHEN** the notifications section is read
- **THEN** it enumerates merge landed, item blocked after retry, and roadmap complete
- **AND** it lists no fourth trigger

#### Scenario: Notification form

- **WHEN** any of the three notifications is sent
- **THEN** it is one line, under 200 characters, and leads with what is actionable

#### Scenario: Silence on dispatch and on idle

- **WHEN** a subagent is dispatched, or a cycle ends with nothing eligible
- **THEN** no notification is sent
- **AND** the skill states both suppressions as rules rather than leaving them as omissions

#### Scenario: Missing notification tool does not fail the run

- **WHEN** `PushNotification` is not available
- **THEN** the cycle continues and completes
- **AND** the run is not failed over the missing notification

### Requirement: Roadmap completion is observed, never performed

"Roadmap complete" SHALL mean that the item just merged was the last unchecked item in its roadmap file. `arbor-auto-work` performs the archival `git mv` into `docs/roadmaps/archive/` inside its own work commit, so this skill SHALL only observe that outcome and notify. It SHALL NOT move, copy, rename, or delete a roadmap file, and SHALL NOT create `docs/roadmaps/archive/`.

#### Scenario: Completion is read off the merged result

- **WHEN** a merge lands and the roadmap file has moved into `docs/roadmaps/archive/`
- **THEN** the cycle treats the roadmap as complete and sends the roadmap-complete notification
- **AND** it performs no move of its own

#### Scenario: The skill never archives

- **WHEN** the skill is read end to end
- **THEN** it contains no instruction to `git mv`, move, or otherwise relocate a roadmap file
- **AND** it states that the archival belongs to `arbor-auto-work`'s work commit

#### Scenario: Merge-landed and roadmap-complete can both fire

- **WHEN** the merged item was the last unchecked item in its file
- **THEN** both the merge-landed and the roadmap-complete notifications are sent
- **AND** neither is described as replacing the other

### Requirement: The skill never authors roadmap content

The skill SHALL NOT author roadmap content in any form: it SHALL NOT write or edit an item's text, SHALL NOT add, remove, or rename a phase, SHALL NOT flip a checkbox in either direction, and SHALL NOT invoke `arbor-auto-roadmap`. The checkbox flip belongs to `arbor-auto-work` inside its work commit. The blocked annotation of the twice-failed item is the single write this skill performs to a roadmap file, and the skill SHALL state explicitly that this annotation is bookkeeping about an item rather than authorship of one.

#### Scenario: Authorship is enumerated and forbidden

- **WHEN** the guardrails are read
- **THEN** they forbid writing items, writing phases, flipping checkboxes, and invoking `arbor-auto-roadmap`, each named

#### Scenario: The flip belongs elsewhere

- **WHEN** a merge lands
- **THEN** the skill does not flip the item's checkbox
- **AND** the skill attributes the flip to `arbor-auto-work`'s work commit

#### Scenario: The annotation is classified as bookkeeping

- **WHEN** the blocked-annotation instruction is read
- **THEN** it states that the annotation is bookkeeping, not authorship
- **AND** the distinction is written into the text rather than left to inference

#### Scenario: No roadmap is created or seeded

- **WHEN** no roadmap exists, or a roadmap has no eligible item
- **THEN** the skill does not create a roadmap, add an item, or invoke `arbor-auto-roadmap` to produce one

### Requirement: The scheduled single-cycle shape survives

The skill SHALL remain a scheduled agent, run roughly hourly — noting that the schedule skill's cron has a one-hour minimum interval — where each run is a single cycle and not a loop. It SHALL NOT loop internally: it exits when the item is handled, or when there is nothing to do, and lets the scheduler bring it back. The cycle SHALL carry the directive `You MUST create a todo per step and complete them in order.`

#### Scenario: One run is one cycle

- **WHEN** the skill is read
- **THEN** it states that each run is a single cycle rather than a loop
- **AND** it directs exiting when done or idle and letting the scheduler return

#### Scenario: Schedule cadence is documented

- **WHEN** the framing is read
- **THEN** it describes the skill as run on a schedule, roughly hourly, and notes the one-hour minimum cron interval

#### Scenario: Todo directive survives

- **WHEN** `grep -n 'You MUST create a todo per step and complete them in order' .claude/skills/arbor-auto-developer/SKILL.md` is run
- **THEN** it matches, on the cycle section

### Requirement: The surviving guardrails are retained

The Guardrails section SHALL retain, with their force intact: that phases are strictly sequential, so a later phase is never worked while an earlier phase still holds an unchecked item; that exactly one subagent is in flight at a time and never two; that at most two attempts (one original plus one retry) are made on the same item in a run; that one run is one cycle with no internal loop; and that the skill only ever touches this repo, under the maintainer's own identity, with no cross-repo activity.

#### Scenario: Strictly sequential phases

- **WHEN** the guardrails are read
- **THEN** the strictly-sequential phase rule is present and stated as a prohibition

#### Scenario: One subagent at a time

- **WHEN** the guardrails are read
- **THEN** the rule that exactly one subagent is in flight, never two, is present

#### Scenario: Repo-scoped identity

- **WHEN** the guardrails are read
- **THEN** the rule that the skill only ever touches this repo, under the maintainer's own identity, is present
- **AND** it names no artifact type the skill no longer uses

### Requirement: Setup is resolved explicitly

The `gh auth` setup step and the integration-branch setup step SHALL both be removed. Whatever remains under Setup SHALL be true of a roadmap-driven, merge-to-`main` skill; if nothing meaningful remains, the section SHALL be dropped entirely. The absence of roadmap files SHALL NOT be represented as a setup failure, because it is a quiet idle run.

#### Scenario: The two removed setup steps are gone

- **WHEN** the finished skill is read
- **THEN** it contains no `gh auth status` step and no step that selects, verifies, or requires an integration branch

#### Scenario: Setup is either true or absent

- **WHEN** the finished skill is read
- **THEN** either there is no Setup section at all, or every step remaining in it is true of a roadmap-driven skill that merges to `main`
- **AND** no remaining step refers to GitHub authentication, issues, labels, or pull requests

#### Scenario: Missing roadmaps are not a setup error

- **WHEN** no roadmap file exists
- **THEN** the skill treats it as a quiet idle run rather than an unmet setup precondition

### Requirement: Frontmatter describes only the surviving behavior and the version is 2.0

The YAML frontmatter `description` SHALL be rewritten to describe only what the rewritten skill does — reading `docs/roadmaps/*.md` as the work queue, selecting one item, dispatching one `arbor-auto-work` subagent, and merging to `main` — and SHALL retain the scheduled, one-cycle-per-run framing. It SHALL NOT describe the pull-request feedback path, the issue backlog, refine self-seeding, or an integration branch, and SHALL NOT name `arbor-auto-refine`. `metadata.version` SHALL be `"2.0"`, replacing `"1.4"`, because this is a rewrite rather than an increment.

#### Scenario: Description matches the body

- **WHEN** the frontmatter `description` is read against the body
- **THEN** every behavior it claims is one the body specifies
- **AND** it claims no behavior the body does not specify

#### Scenario: Scheduled framing retained

- **WHEN** the frontmatter `description` is read
- **THEN** it states that the skill runs on a schedule and that each run is a single cycle, not a loop

#### Scenario: Removed concerns absent from the description

- **WHEN** the frontmatter `description` is read
- **THEN** it mentions no pull request, no issue backlog, no label, no integration branch, and no self-seeding
- **AND** it does not contain the string `arbor-auto-refine`

#### Scenario: Version bumped to 2.0

- **WHEN** `metadata.version` is read
- **THEN** its value is `"2.0"`
- **AND** the frontmatter still parses as YAML with `name`, `description`, `license`, and `metadata` present

### Requirement: The foreground goal mode is not added by this change

This change SHALL NOT add a `--goal` flag, a foreground mode, an internal loop over multiple items, or any behavior that works more than one item per invocation. That is roadmap item R5, shipping after this change and extending what is written here. The skill's default SHALL remain one cycle per invocation.

#### Scenario: No goal mode appears

- **WHEN** the finished skill is searched for `--goal`, `foreground`, and any instruction to keep working items until a roadmap is finished
- **THEN** none of them appears

#### Scenario: Default remains one cycle

- **WHEN** the skill is read
- **THEN** it works exactly one item per invocation and then exits

### Requirement: Change scope is limited to the auto-developer skill

Implementing this change SHALL modify only `.claude/skills/arbor-auto-developer/SKILL.md` and the OpenSpec artifacts for this change. The skills `arbor-auto-work`, `arbor-auto-roadmap`, `arbor-opsx-auto`, and `arbor-project-scaffold` SHALL NOT be created, modified, moved, or deleted, and no new skill directory SHALL be added. No `docs/roadmaps/archive/` directory, placeholder, or `.gitkeep` SHALL be created or committed by this change. `docs/roadmaps/roadmap-native-workcycles.md` SHALL be read for context and SHALL NOT be modified — R4's own checkbox is flipped outside this change, by `arbor-auto-work`'s commit step.

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
