## 1. Inputs — document the token

- [x] 1.1 Add the `roadmap:docs/roadmaps/<slug>.md#R<n>` token to the **Inputs** section of `.claude/skills/arbor-auto-work/SKILL.md`, listed alongside the type, the mode flags, and the per-phase model tokens. Verify: the section names the token, gives its form, and the addition reads in the section's existing prose voice rather than as a bolted-on list.
- [x] 1.2 State in **Inputs** that the token is optional and that omitting it runs the cycle unchanged — no flip, no roadmap bullet, no error. Verify: the word "optional" (or an equally unambiguous statement) is present, and nothing in the file implies every run must carry a reference.
- [x] 1.3 State in **Inputs** that the reference names the roadmap item this cycle is building, matching the format `arbor-auto-roadmap` defines. Verify: the format string matches `docs/roadmaps/<slug>.md#R<n>` exactly as documented in `.claude/skills/arbor-auto-roadmap/SKILL.md`.

## 2. Step 0 — strip, then validate

- [x] 2.1 Extend step 0 so the `roadmap:` token is set aside together with the `spec:`/`work:`/`gate:`/`archive:` tokens and the `--interaction`/`--pr` flags, and so the existing rationale sentence covers it: keeping it out now ensures it never leaks into the work-ID slug in steps 2–3. Verify: step 0 names the roadmap token in the same strip instruction, and the rationale sentence no longer reads as covering only the model tokens.
- [x] 2.2 State explicitly in step 0 that the roadmap reference is retained by this skill and is **not** forwarded to `arbor-opsx-auto`, unlike the model tokens. Verify: the non-forwarding claim is present in step 0, and step 4's forwarding sentence still names the model tokens as what it forwards.
- [x] 2.3 Add validation to step 0, performed immediately after the strip and before the branch is created in step 3: confirm the referenced file exists, that an item with the given `R<n>` exists in it, and that the item's box is currently unchecked. Verify: the validation is anchored to step 0 in the text, and the ordering "before any branch or lifecycle work" is explicit rather than inferable.
- [x] 2.4 Name all three failure cases explicitly as hard errors that stop the run — missing file, missing `R<n>`, already-checked item — and forbid the workarounds: no creating the file, no appending the item, no falling back to a different item, no downgrade to a warning, no silent skip. Verify: all three cases appear by name, and each is attached to stopping the run rather than to a recovery action.
- [x] 2.5 Note that a reference into a roadmap that has already been archived resolves as a missing file and is therefore a hard error — the skill does not search `docs/roadmaps/archive/` for the item. Verify: the archived-roadmap case is addressed, and no instruction directs a fallback lookup in the archive directory.

## 3. Step 5 — flip the item

- [x] 3.1 Insert the flip into step 5 **before** the commit is authored: rewrite the referenced item from `- [ ] **R<n>**` to `- [x] **R<n>**`. Verify: the instruction sits inside step 5, ahead of the commit instruction, and no new step number and no post-merge action is introduced.
- [x] 3.2 Require that the target line is re-confirmed to be in the unchecked form immediately before the rewrite. Verify: the re-confirmation is stated, so the rewrite cannot no-op silently or land on the wrong line.
- [x] 3.3 Scope the edit to the checkbox marker on the line carrying `**R<n>**`, leaving the item's text and its wrapped continuation lines byte-identical. Verify: the text forbids re-wording or reflowing the item, so the roadmap diff for a flip is a single-character change.
- [x] 3.4 State that the flip lands in the same commit, on the same branch, as the work — no separate bookkeeping commit and no separate push. Verify: the atomicity claim is present in step 5.

## 4. Step 5 — archive a completed roadmap

- [x] 4.1 Add the completion test: after the flip, if no line matching the unchecked item form `- [ ] **R<n>**` remains anywhere in the file, the roadmap is complete. Verify: the test is written against the unchecked item form rather than a bare `- [ ]`, and it is not phrased as a positional "was this the last line" check.
- [x] 4.2 Instruct that the completed roadmap is moved with `git mv` to `docs/roadmaps/archive/`, staged into the same commit as the flip and the work. Verify: `git mv` is named (not a plain `mv` plus `git add`), and the same-commit requirement is explicit.
- [x] 4.3 Instruct that `docs/roadmaps/archive/` is created before the move, because it may not exist — git tracks no empty directory, so the first archival in any repo is the moment it comes into being. Verify: a directory-creation step precedes the `git mv` in the text, so the move cannot fail on a missing destination.
- [x] 4.4 Fix the ordering: the content edit happens before the move, so the archived file contains the checked box. Verify: the two actions appear in that order and the reason is stated.
- [x] 4.5 State that a file still holding an unchecked item is not moved. Verify: the non-archival path is explicit, so archival is not read as unconditional after a flip.

## 5. Step 5 — commit body

- [x] 5.1 Add the `- Roadmap: <slug> R<n> complete` bullet to the commit-body rules, applied whenever a reference was supplied, with `<slug>` defined as the roadmap filename without its `.md` extension. Verify: the bullet string matches character for character, and `<slug>` is defined in the file rather than left to inference.
- [x] 5.2 Add the `- Roadmap <slug> complete; archived` bullet for the archival case, stated as accompanying the first bullet rather than replacing it. Verify: the bullet string matches character for character (note it carries no colon after `Roadmap`, unlike the first — reproduce both verbatim), and the "in addition to" relationship is explicit.
- [x] 5.3 Confirm the roadmap bullets coexist with the existing environment-blocked bullet in one commit body. Verify: nothing in the new text implies the bullets are alternatives, and the existing environment-blocked example bullet is untouched.

## 6. Preserve the gate and environment-blocked contracts

- [x] 6.1 State at the flip that reaching step 5 is itself the precondition — a genuine gate failure or an incomplete task stops the cycle in step 4, so the flip is never reached on a failed run. Verify: the precondition is stated where the flip is described, and step 4's own stopping rule is unmodified.
- [x] 6.2 Read every sentence added for the roadmap concern and confirm none directs, implies, or permits closing an item as bookkeeping independent of the gate outcome. Verify: no added sentence promises an unconditional flip; phrases like "always close the item" do not appear.
- [x] 6.3 Add one Guardrails bullet tying the flip to the existing gate rule, without weakening any existing guardrail. Verify: the pre-existing guardrails (gate failure stops at step 4; environment-blocked is the only skip and must leave a visible trace; one change = one work ID = one branch) are still present with their wording and force intact.
- [x] 6.4 State that an environment-blocked stage still flips and still archives, and still carries its existing visible trace bullet in the same commit body. Verify: the environment-blocked path explicitly reaches the flip, and the existing `- E2E skipped: environment-blocked (<reason>); not independently verified.` example survives verbatim.

## 7. Frontmatter

- [x] 7.1 Update the frontmatter `description` to mention the `roadmap:` token alongside the existing model tokens, keeping it a routing description rather than a second copy of **Inputs**. Verify: the description names the token, still fits the file's existing one-paragraph description style, and describes nothing the body does not do.
- [x] 7.2 Bump `metadata.version` from `1.1` to `1.2`. Verify: the frontmatter parses and the value is greater than the previous one.

## 8. Structure, scope, and final verification

- [x] 8.1 Confirm the **Steps** section still runs 0 through 7, each step keeping its current subject, and that the file's section headings are unchanged. Verify: no step was added, removed, renumbered, or repurposed, and no new top-level section exists.
- [x] 8.2 Confirm every pre-existing rule survives: the autonomous/interactive/`--pr` mode framing, the `<TYPE>-<n>-<slug>` work-ID rule with its `ls | grep -oE` numbering command, the `feature|bugfix|hotfix/<id>-<slug>` branch rule, the `arbor-opsx-auto` delegation with its production-standard bar and gate read-back, the push step, and the integrate/PR step. Verify: each is present and unedited except where the roadmap concern required a change.
- [x] 8.3 Confirm the working tree changes nothing outside `.claude/skills/arbor-auto-work/SKILL.md` and `openspec/`. Verify: `git status --porcelain` lists no other path, and specifically no path under `.claude/skills/arbor-opsx-auto/`, `arbor-auto-developer/`, `arbor-auto-roadmap/`, or `arbor-project-scaffold/`, and no new skill directory.
- [x] 8.4 Confirm no `docs/roadmaps/archive/` directory, placeholder, or `.gitkeep` was created or committed by this change. Verify: the path does not appear in `git status --porcelain` and does not exist in the working tree.
- [x] 8.5 Confirm `docs/roadmaps/roadmap-native-workcycles.md` is untouched — R3's own checkbox is flipped outside this change, by hand. Verify: it does not appear in `git status --porcelain`.
- [x] 8.6 Read the edited `SKILL.md` end to end against every requirement in `specs/work-cycle/spec.md`, and diff it against the pre-change version to confirm the edit touched only **Inputs**, step 0, step 5, the frontmatter, and one guardrail bullet. Verify: every scenario holds when read literally, and the diff shows no unintended drift.
