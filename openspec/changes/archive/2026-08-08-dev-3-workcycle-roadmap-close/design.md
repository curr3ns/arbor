## Context

This is a skills repo: the product is Markdown skill definitions at `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, and no gate command. "Implementation" here means editing one Markdown file, and the bar is prose precise enough that a future agent following it literally does the right thing in every case the acceptance criteria name. Verification is reading the file back against those criteria plus greppable checks.

`.claude/skills/arbor-auto-work/SKILL.md` (v1.1, 91 lines) is the mandatory work cycle. It has three sections — **Inputs**, **Steps** (numbered 0–7), and **Guardrails** — and its shape today is:

- **0** strip `spec:`/`work:`/`gate:`/`archive:` model tokens and `--interaction`/`--pr` flags off the description, explicitly so they cannot leak into the work-ID slug;
- **1–3** restate the slice, assign `<TYPE>-<n>-<slug>`, create the branch;
- **4** delegate propose → apply → gate → archive to `arbor-opsx-auto`, forwarding the model tokens verbatim; read back its gate outcome; a genuine gate failure or incomplete task stops the cycle here;
- **5** commit, with a bullet surfacing an environment-blocked stage when step 4 reported one;
- **6–7** push, then merge / open a PR.

The surrounding system state matters. R1 redefined a checked roadmap box to mean "implemented, gated, and merged" and defined the item reference `docs/roadmaps/<slug>.md#R<n>` as *an argument handed to `arbor-auto-work`*; R2 deleted `arbor-auto-refine`, which had been the only skill that ever flipped a box (at issue-filing time, which under the new semantics was a lie). So the producer side of the contract exists and the old consumer is gone: nothing closes an item. This change makes `arbor-auto-work` the consumer, which is item R3 of `docs/roadmaps/roadmap-native-workcycles.md`.

The alternative placements were all considered and rejected upstream, and the roadmap records why: a flip inside the work cycle rides in the same commit on the same branch as the work, so it lands atomically on merge, needs no separate bookkeeping push, has no push race, and works the same for a scheduled agent and a human. Everything below follows from committing to that.

## Goals / Non-Goals

**Goals:**

- One new optional input token, `roadmap:docs/roadmaps/<slug>.md#R<n>`, stripped in step 0 and documented in **Inputs**.
- A pre-commit flip inside step 5, plus archival of a fully-checked roadmap in that same commit.
- Commit-body bullets that make the bookkeeping visible in `git log`.
- Three named hard-error cases for a bad reference, each stopping the run.
- The gate contract and the environment-blocked contract left exactly as strong as they are today.
- Frontmatter `description` and `metadata.version` updated.

**Non-Goals:**

- **Touching `arbor-opsx-auto`.** It runs branch-local and leaves everything uncommitted, so it owns no commit and has no roadmap concern. An explicit non-goal of the parent roadmap.
- **Touching `arbor-auto-developer`, `arbor-auto-roadmap`, or `arbor-project-scaffold`.** Developer learns to pass the token at R4; scaffold creates `docs/roadmaps/archive/` for new projects at R6; roadmap is already done at R1/R2.
- **Creating `docs/roadmaps/archive/` in this repo.** See D5.
- **Any new skill, and any new file outside this change's OpenSpec directory.**
- **Restructuring the skill.** Section headings and step numbers 0–7 stay as they are.
- **Flipping R3's own box in `docs/roadmaps/roadmap-native-workcycles.md`.** That bookkeeping is handled outside this change.

## Decisions

**D1 — The token is stripped in step 0 with the model tokens, but is *not* forwarded to `arbor-opsx-auto`.**
Step 0's stated purpose is that stripped tokens "never leak into the work-ID slug in steps 2–3," and the roadmap ref is the most dangerous thing yet to leak: it is a path containing `/`, `.`, and `#`, which would produce a garbage slug and therefore a garbage work ID and branch name. So it joins the same strip.

It must *not* join the same forward. Step 4 hands the model tokens to `arbor-opsx-auto` verbatim; the roadmap ref stops in this skill, because `arbor-opsx-auto` commits nothing and has no roadmap concern. The instruction must say both halves explicitly — "set aside" and "forwarded verbatim" sit two sentences apart in the current text, and an agent skimming step 0 could reasonably infer that everything stripped in 0 is forwarded in 4. Alternative considered: introduce the token as a `--roadmap <ref>` flag alongside `--interaction`/`--pr` instead of a `key:value` token. Rejected — it takes a value, and the file's established shape for a token that takes a value is `prefix:value`. Consistency with `spec:`/`work:`/`gate:`/`archive:` makes the strip rule one rule rather than two.

**D2 — Validate the reference at step 0, at the moment it is stripped; re-confirm at the flip.**
This is the one genuine design choice in the change. The acceptance criterion only requires that a bad ref be a hard error that stops the run, which lazy validation at step 5 would technically satisfy. It satisfies it badly: by step 5 the run has created a branch, run a full OpenSpec lifecycle, and passed a gate, and the tree is full of uncommitted work with no commit to hold it. Stopping there converts a typo into a manual-recovery situation.

Every input the check needs — the file, the item, its checkbox state — is on disk before any work starts, so the check is free at step 0 and the run stops before the branch exists. Step 5 then re-confirms that the target line is still in the unchecked `- [ ] **R<n>**` form immediately before rewriting it. The re-confirmation is not paranoia about concurrency inside a single run; it is what makes the rewrite instruction self-checking, so an agent cannot "flip" by appending, by rewriting the wrong line, or by silently no-oping on a line that no longer matches.

**D3 — All three bad-ref cases are enumerated by name, and the error is hard.**
Missing file, missing `R<n>` in a file that does exist, and an item already checked. Terse prose ("if the reference doesn't resolve, error") invites an agent to pattern-match the most familiar case and treat the other two as "nothing to do" — an already-checked item in particular reads like an idempotent no-op, and silently skipping it is exactly the failure this whole item exists to prevent, since it means the work just built was attributed to an item someone else already closed. Naming all three costs three clauses and removes the inference.

Two consequences worth stating in the skill: a ref pointing at a roadmap that has already been archived resolves to a missing file (the path is `docs/roadmaps/<slug>.md`, and archival moved it to `docs/roadmaps/archive/`), so it is correctly a hard error; and **no ref at all is not an error** — the token is optional, and work that is not on a roadmap is the ordinary case. Without that second statement, hardening the error cases risks an agent inventing a requirement that every run carry a ref.

**D4 — The flip goes inside step 5 before the commit, not into a new step.**
A new step 5.5, or a step 8 after the merge, would both break the numbering and the "one todo per step" instruction, and step 8 would additionally give up atomicity — the whole point of R3. Putting it inside step 5, before the commit is authored, means the flip, the archival, and the work are one commit and one merge. It also puts the flip physically adjacent to the commit-bullet rules that describe it, so an agent reading step 5 sees the action and its trace together.

**D5 — Archive with `mkdir -p` then `git mv`, content edit first.**
`git mv` fails when the destination directory does not exist, and `docs/roadmaps/archive/` does not exist in this repo — git does not track empty directories, so nothing has ever created it. The instruction therefore creates the directory before the move. This change does **not** ship the directory (with or without a `.gitkeep`): that would be a file outside the declared single-file scope, it would need to exist in every downstream repo anyway rather than just this one, and R6 owns creating it during project scaffolding. Creating it on demand at the moment of first use is the only variant that works everywhere.

Order matters and must be stated: rewrite the checkbox first, then move the file, so the archived copy contains the checked box; then stage both the modification and the rename into the one commit.

**D6 — "Every item is checked" is tested as "no unchecked item line remains."**
Concretely: no line matching the unchecked item form `- [ ] **R<n>**` survives anywhere in the file after the flip. Alternatives considered: counting items and comparing to a checked count (needs two scans and a correct notion of what an item is), or tracking whether this was "the last" item by position (wrong — items are not worked in file order once phases interleave, and the last unchecked item is rarely the last line). Scanning for the unchecked form is one check, it matches the criterion's literal wording, and it stays correct when items are added or dropped between cycles. Matching the full `- [ ] **R<n>**` form rather than a bare `- [ ]` avoids counting an unrelated checklist line or a fenced template example as an outstanding item.

**D7 — The rewrite touches only the marker on the item's first line.**
Roadmap items wrap across many indented continuation lines — the items in `roadmap-native-workcycles.md` run five to twenty lines each. The instruction must scope the edit to the `- [ ]` → `- [x]` marker on the line carrying `**R<n>**`, leaving the item's text and its continuation lines byte-identical. An unscoped "rewrite the item" invites reflowing or re-wording the item, which would silently edit the roadmap's content under cover of a bookkeeping commit.

**D8 — The two commit bullets are used verbatim, asymmetry included.**
`- Roadmap: <slug> R<n> complete` and `- Roadmap <slug> complete; archived` — the first has a colon after `Roadmap`, the second does not. These are the strings the parent roadmap's acceptance criteria specify, so reproducing them exactly keeps the criteria checkable by grep and keeps this skill agreeing with the roadmap and with R4's future expectations. Normalizing the punctuation would be tidier and is rejected for exactly that reason. `<slug>` is defined in the skill as the roadmap filename without its `.md` extension (e.g. `roadmap-native-workcycles`), so the bullet stays short and stable when the file moves to the archive. The second bullet appears **in addition to** the first, never instead of it.

**D9 — The gate contract is restated, not re-litigated.**
The flip lives at step 5, and step 4 already stops the cycle on a genuine gate failure or an incomplete task, so the flip is unreachable on a failed run without any new machinery. The risk is purely textual: new step-5 prose about "always closing the item" could be read as licence to flip for bookkeeping after a failure. The mitigation is to say plainly, where the flip is described, that reaching step 5 is itself the precondition, and to add one Guardrails bullet tying the flip to the existing gate rule. No existing guardrail wording is weakened, and nothing in step 4 changes.

**D10 — An environment-blocked stage flips, and both bullets appear together.**
Environment-blocked is already an accepted outcome that proceeds to commit, push, and merge, on the condition that it leaves a visible trace. Suppressing the flip in that case would invent a fourth roadmap state ("built but not closed") that nothing in the system knows how to resolve, and would strand the item for the next cycle to re-attempt work that already landed. So it flips, and the commit body carries the roadmap bullet *and* the existing `- E2E skipped: environment-blocked (<reason>); not independently verified.` bullet — the trace travels with the flip in one commit rather than being traded against it.

**D11 — Version `1.2`, and a `description` that advertises the token.**
The repo bumps skill versions in minor steps (`arbor-auto-roadmap` ran 1.2 → 1.3 → 1.4 across R1 and R2); `1.1` → `1.2` follows. Nothing consumes `metadata.version` as a compatibility signal, so the sequence is documentation and the repo convention wins over semver theatre. The `description` is routing text: it already enumerates the accepted model tokens, so an agent deciding whether `arbor-auto-work` can take a roadmap ref reads it there. It must name the token without growing into a second copy of the Inputs section.

**D12 — Retire the previous change's scope requirement in `roadmap-planning`.**
`dev-2-delete-auto-refine` left a live requirement, *Change scope is limited to refine deletion and the roadmap scrub*, asserting that `arbor-auto-work` SHALL NOT be modified. That fence existed to bound that change and is now superseded by this one, which modifies exactly that file. Leaving it would put the live spec set in direct contradiction with itself. Removing it follows the precedent `dev-2` set when it retired R1's equivalent fence, and it is bookkeeping only — no file under `.claude/skills/arbor-auto-roadmap/` changes and no behavior of `arbor-auto-roadmap` changes. This change carries its own scope requirement in `work-cycle` in its place.

## Risks / Trade-offs

- **New step-5 prose reads as "always close the item," undercutting the gate** → Mitigated by D9: the precondition is stated at the flip, one guardrail bullet ties it to the existing rule, and a task verifies no sentence promises a flip independent of reaching step 5.
- **An agent forwards the `roadmap:` token to `arbor-opsx-auto` because step 0 strips it next to tokens step 4 forwards** → Mitigated by D1: step 0 says the roadmap ref is not forwarded, and step 4's forwarding sentence stays scoped to the model tokens by name.
- **The flip silently no-ops on an already-checked item, attributing new work to a closed item** → Mitigated by D2 and D3: validated at step 0 before any work, named as one of three hard errors, and re-confirmed at the rewrite.
- **`git mv` fails on the very first archival because `docs/roadmaps/archive/` does not exist** → Mitigated by D5: the instruction creates the directory first, and this is the first thing the archival task verifies.
- **The archived file is committed with the box still unchecked** → Mitigated by D5's stated ordering (edit, then move) and by a task that checks the ordering is explicit in the prose rather than implied.
- **The bookkeeping commit quietly reflows or re-words roadmap item text** → Mitigated by D7: the edit is scoped to one marker on one line, and the diff for that file must be a single-character change (plus a rename when archiving).
- **The token is optional, so a caller that forgets it merges work and leaves the box open** → Accepted. Making it mandatory would break every non-roadmap invocation of the mandatory work cycle. R4 makes the automated caller always pass it; a human running the skill by hand and omitting it gets the pre-change behavior, which is a safe default.
- **The first consumer ships with no automated producer until R4** → Accepted, and it is the hand-run path the acceptance criteria explicitly require to work. The format is fixed by R1 and is trivial (path + `#` + ID), so there is no interface to get wrong in the interim.
- **Threading a new concern through an existing 91-line prompt risks bloating it into a different skill** → Mitigated by holding the edit to three sites (**Inputs**, step 0, step 5) plus frontmatter and one guardrail bullet, and by a final task that diffs old against new to confirm nothing else moved.

## Migration Plan

Single-file edit; no rollout, no data migration, nothing to deploy. Rollback is `git checkout` of `.claude/skills/arbor-auto-work/SKILL.md`. Behavior is backward compatible in both directions: an invocation with no `roadmap:` token behaves exactly as it does today, and older invocations continue to work unchanged. Downstream repos pick the change up the next time `install.sh` refreshes their skill symlinks — the skills are symlinked, not copied, so there is nothing to version-pin.

## Open Questions

None blocking. Two things are deliberately left to later roadmap items: `arbor-auto-developer` passing the token on every cycle (R4), and `docs/roadmaps/archive/` existing from the start in freshly scaffolded projects (R6). Neither is needed for this change to be correct on its own.
