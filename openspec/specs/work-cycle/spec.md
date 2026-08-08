## ADDED Requirements

### Requirement: The work cycle accepts an optional roadmap item reference

The `arbor-auto-work` skill SHALL accept an optional input token of the form `roadmap:docs/roadmaps/<slug>.md#R<n>`, naming the roadmap item the work cycle is building. The token SHALL be documented in the skill's **Inputs** section alongside the type, the mode flags, and the per-phase model tokens. The token SHALL be documented as optional: an invocation that passes no `roadmap:` token SHALL run the full cycle unchanged, with no roadmap flip, no roadmap commit bullet, and no error.

#### Scenario: Token is documented as an input

- **WHEN** the **Inputs** section of `.claude/skills/arbor-auto-work/SKILL.md` is read
- **THEN** it names the `roadmap:` token and gives its form as `docs/roadmaps/<slug>.md#R<n>`
- **AND** it states that the token is optional

#### Scenario: Omitting the token is the ordinary path

- **WHEN** `arbor-auto-work` is invoked with no `roadmap:` token
- **THEN** the skill performs no roadmap lookup, no flip, and no archival
- **AND** it does not treat the absence as an error or a warning
- **AND** the commit body carries no roadmap bullet

### Requirement: The roadmap token is stripped in step 0 and never reaches the work ID

Step 0 SHALL set the `roadmap:` token aside together with the `spec:`/`work:`/`gate:`/`archive:` model tokens and the `--interaction`/`--pr` flags, so that what remains is the work description used everywhere else. The stripped reference SHALL NOT appear in the work description that produces the `<slug>` in step 2 or the branch name in step 3.

#### Scenario: Reference is removed before the slug is built

- **WHEN** `arbor-auto-work` is invoked with a description followed by `roadmap:docs/roadmaps/roadmap-native-workcycles.md#R3`
- **THEN** step 0 removes the token from the description
- **AND** the change name assigned in step 2 and the branch created in step 3 contain no fragment of the path, no `#`, and no `R3` derived from the reference

#### Scenario: Step 0 states why the token is stripped

- **WHEN** step 0 is read
- **THEN** it gives the same rationale for the roadmap token as for the model tokens — that stripping it now keeps it out of the work-ID slug built in steps 2–3

### Requirement: The roadmap reference is not forwarded to the OpenSpec lifecycle

The skill SHALL forward only the model tokens set aside in step 0 to `arbor-opsx-auto` in step 4. The `roadmap:` reference SHALL be retained by `arbor-auto-work` and SHALL NOT be forwarded, because `arbor-opsx-auto` runs branch-local, produces no commit, and has no roadmap concern.

#### Scenario: Forwarding is scoped to the model tokens

- **WHEN** step 0 and step 4 are read together
- **THEN** the text states that the roadmap reference stays in this skill and is not passed to `arbor-opsx-auto`
- **AND** step 4's forwarding instruction names the model tokens as what is forwarded

### Requirement: A roadmap reference is validated before any work begins

When a `roadmap:` token is supplied, the skill SHALL resolve and validate it in step 0, immediately after stripping it and before the branch is created in step 3. Validation SHALL confirm that the referenced file exists, that a roadmap item with the given `R<n>` identifier exists in that file, and that the item's checkbox is currently unchecked.

#### Scenario: Validation happens before the branch exists

- **WHEN** step 0 is read
- **THEN** it directs that a supplied reference is resolved and checked at that point
- **AND** an invalid reference stops the run before any branch is created and before the OpenSpec lifecycle is invoked

#### Scenario: A valid reference proceeds silently

- **WHEN** the referenced file exists, contains an unchecked item with the given identifier, and the run continues
- **THEN** no additional prompt, confirmation, or approval is introduced by the roadmap concern

### Requirement: Three bad-reference cases are hard errors that stop the run

The skill SHALL treat each of the following as a hard error that stops the run, and SHALL name all three explicitly: a reference whose file is not present; a reference whose `R<n>` identifier is not found in a file that is present; and a reference to an item whose box is already checked. None of the three SHALL be silently ignored, skipped, treated as a no-op, downgraded to a warning, or worked around by creating the file, creating the item, or choosing a different item.

#### Scenario: Missing file

- **WHEN** the reference names `docs/roadmaps/<slug>.md` and no such file exists
- **THEN** the run stops with an error naming the unresolvable file
- **AND** the skill does not create the file and does not continue without a roadmap reference

#### Scenario: Missing item

- **WHEN** the referenced file exists but contains no item with the given `R<n>` identifier
- **THEN** the run stops with an error naming the missing identifier
- **AND** the skill does not append a new item and does not fall back to another item

#### Scenario: Already-checked item

- **WHEN** the referenced item exists but its box is already `- [x] **R<n>**`
- **THEN** the run stops with an error
- **AND** the skill does not treat the flip as an idempotent no-op and does not proceed to attribute new work to an item that is already closed

#### Scenario: Reference into an archived roadmap

- **WHEN** the referenced roadmap has already been moved to `docs/roadmaps/archive/`, so `docs/roadmaps/<slug>.md` no longer exists
- **THEN** the reference resolves as a missing file and the run stops, rather than searching the archive directory for the item

### Requirement: The referenced item is flipped inside step 5 before the commit

When a valid `roadmap:` reference was supplied, step 5 SHALL rewrite the referenced item from `- [ ] **R<n>**` to `- [x] **R<n>**` before the commit is authored, so that the flip lands in the same commit, on the same branch, as the work itself. The skill SHALL confirm the target line is still in the unchecked form immediately before rewriting it. The edit SHALL change only the checkbox marker on the line carrying the item's identifier; the item's text and any wrapped continuation lines SHALL be left byte-identical.

#### Scenario: Flip precedes the commit in the same step

- **WHEN** step 5 is read
- **THEN** the flip is described as happening before the commit is made, within step 5
- **AND** no separate step, later step, or post-merge action is introduced for it

#### Scenario: Only the marker changes

- **WHEN** the flip is applied to an item whose text wraps across several indented lines
- **THEN** the resulting diff for the roadmap file changes only `- [ ]` to `- [x]` on the line carrying `**R<n>**`
- **AND** the item's wording, wrapping, and continuation lines are unchanged

#### Scenario: Flip and work land together

- **WHEN** the commit created in step 5 is inspected
- **THEN** it contains both the work and the roadmap flip
- **AND** no additional commit or push is required to record the flip

### Requirement: A fully-checked roadmap is archived in the same commit

After the flip, when no line matching the unchecked item form `- [ ] **R<n>**` remains anywhere in the roadmap file, step 5 SHALL move that file to `docs/roadmaps/archive/` with `git mv`, staged into the same commit as the flip and the work. Because `docs/roadmaps/archive/` may not exist, the skill SHALL create the directory before the move. The content edit SHALL be made before the move, so the archived file contains the checked box.

#### Scenario: Last item triggers archival

- **WHEN** the flipped item was the only remaining unchecked item in the file
- **THEN** the roadmap file is moved to `docs/roadmaps/archive/` with `git mv`
- **AND** the move is staged into the same commit as the flip and the work

#### Scenario: Archive directory is created on demand

- **WHEN** `docs/roadmaps/archive/` does not exist at the moment of the first archival
- **THEN** the skill creates it before invoking `git mv`, so the move does not fail on a missing destination

#### Scenario: Remaining unchecked items suppress archival

- **WHEN** at least one line matching `- [ ] **R<n>**` remains in the file after the flip
- **THEN** the file is not moved and stays at `docs/roadmaps/<slug>.md`

#### Scenario: Archived file carries the checked box

- **WHEN** the archived roadmap is read after the commit
- **THEN** the item flipped by this run appears as `- [x] **R<n>**`, because the content edit was made before the move

### Requirement: The commit body records the roadmap outcome

When a `roadmap:` reference was supplied, the commit created in step 5 SHALL include the bullet `- Roadmap: <slug> R<n> complete`, where `<slug>` is the roadmap filename without its `.md` extension. When the flip also archived the roadmap, the commit SHALL additionally include the bullet `- Roadmap <slug> complete; archived`. The second bullet SHALL accompany the first, never replace it.

#### Scenario: Item-complete bullet

- **WHEN** a run passes `roadmap:docs/roadmaps/roadmap-native-workcycles.md#R3` and reaches the commit
- **THEN** the commit body contains `- Roadmap: roadmap-native-workcycles R3 complete`

#### Scenario: Roadmap-complete bullet accompanies it

- **WHEN** that item was the last unchecked item and the file was archived
- **THEN** the commit body contains both `- Roadmap: roadmap-native-workcycles R3 complete` and `- Roadmap roadmap-native-workcycles complete; archived`

#### Scenario: No bullet without a reference

- **WHEN** no `roadmap:` token was supplied
- **THEN** the commit body contains no roadmap bullet

### Requirement: A genuine gate failure never reaches the flip

The skill SHALL preserve the existing rule that a genuine gate failure or an incomplete task stops the cycle in step 4, before the commit. No text introduced for the roadmap concern SHALL state, imply, or permit that an item is flipped, archived, or recorded as complete when step 5 was not reached. The skill SHALL state, where the flip is described, that reaching step 5 is itself the precondition for it.

#### Scenario: Gate failure stops before any roadmap change

- **WHEN** step 4 reports a genuine gate failure
- **THEN** the cycle stops there
- **AND** no roadmap file is edited, moved, or committed

#### Scenario: No text promises an unconditional flip

- **WHEN** the roadmap text added to step 5 and the guardrails is read
- **THEN** no sentence directs closing the item as bookkeeping independent of the gate outcome
- **AND** the existing guardrail that a genuine gate failure stops the cycle at step 4 survives with its force intact

### Requirement: An environment-blocked stage still flips and still leaves a trace

When step 4 reports an environment-blocked stage, the skill SHALL still perform the flip and any resulting archival, and SHALL still surface the blocked stage in the commit body in the existing form, for example `- E2E skipped: environment-blocked (<reason>); not independently verified.`. The roadmap bullets and the environment-blocked bullet SHALL appear together in the same commit body.

#### Scenario: Blocked stage does not suppress the flip

- **WHEN** step 4 reports an environment-blocked stage and a valid `roadmap:` reference was supplied
- **THEN** the item is flipped and the commit is made

#### Scenario: Trace accompanies the flip

- **WHEN** that commit body is read
- **THEN** it contains the roadmap bullet and the environment-blocked bullet naming the reason
- **AND** the existing rule that a skipped stage must leave a visible trace is unchanged

### Requirement: Frontmatter advertises the token and the version is bumped

The skill's YAML frontmatter `description` SHALL mention the `roadmap:` token, so an agent routing on the description can tell that `arbor-auto-work` accepts a roadmap item reference. The `metadata.version` value SHALL be increased above its previous value of `1.1`.

#### Scenario: Description mentions the token

- **WHEN** the frontmatter `description` is read
- **THEN** it names the `roadmap:` token alongside the existing model tokens
- **AND** it remains a description rather than a second copy of the **Inputs** section

#### Scenario: Version bumped

- **WHEN** `metadata.version` is compared against the previous value `1.1`
- **THEN** the new value is greater

### Requirement: The skill's existing structure and voice are preserved

The change SHALL thread the roadmap concern through the existing **Inputs** section, step 0, and step 5, and SHALL NOT restructure the skill. The step numbering SHALL remain 0 through 7 with each step keeping its current subject, and the existing section headings SHALL be retained. The two-mode framing, the work-ID and branch conventions, the delegation of propose/apply/gate/archive to `arbor-opsx-auto`, the push step, the integrate step, and the existing guardrails SHALL survive with their meaning intact.

#### Scenario: Step numbering unchanged

- **WHEN** the **Steps** section is read after the change
- **THEN** it still runs 0 through 7
- **AND** each numbered step covers the same subject it covered before

#### Scenario: No new sections

- **WHEN** the file's headings are compared before and after
- **THEN** the same top-level sections are present, with no section added or removed for the roadmap concern

#### Scenario: Pre-existing rules survive

- **WHEN** the skill is read end to end
- **THEN** the autonomous/interactive modes, the `<TYPE>-<n>-<slug>` work-ID rule, the `feature|bugfix|hotfix/<id>-<slug>` branch rule, the `arbor-opsx-auto` delegation with its production-standard bar, the push step, the integrate/PR step, and the one-change-one-work-ID-one-branch guardrail are all still present

