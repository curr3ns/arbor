## Context

This is a skills repo: the product is Markdown skill definitions at `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, and no gate command — "implementation" here means rewriting one Markdown file, and verification means reading it back against acceptance criteria.

`.claude/skills/arbor-auto-roadmap/SKILL.md` (v1.2, 129 lines) today does four things:

1. Interrogates a human about product direction via `AskUserQuestion` (name/vision, non-goals, phases, items per phase), recaps, and only then generates. **This is the heart of the skill and does not change.**
2. Branches on an output format chosen in step 1: files under `docs/roadmap/` (singular) *or* GitHub Milestones plus a pinned tracking issue, gated by a GitHub-only Setup section.
3. Defines a `Roadmap:` reference line — a literal line placed in a GitHub issue body by `arbor-auto-refine` — in two dialects, one per format.
4. States guardrails, including that a checked box means "refined into the backlog," flipped by `arbor-auto-refine` at issue-filing time.

Parent roadmap item R1 in `docs/roadmaps/roadmap-native-workcycles.md` inverts the model: the roadmap file *is* the work queue, `arbor-auto-work` flips the box after the work is gated and merged, and the GitHub issue backlog disappears. Items 2–4 above are therefore obsolete in their current form.

## Goals / Non-Goals

**Goals:**

- One roadmap format: files at `docs/roadmaps/<slug>.md`, archiving to `docs/roadmaps/archive/`.
- Checkbox semantics redefined to "implemented, gated, and merged."
- A single, file-scoped `R<n>` ID rule.
- An item-reference format `docs/roadmaps/<slug>.md#R<n>` described as an argument handed to `arbor-auto-work`, not as text in an issue body.
- Frontmatter `description` rewritten to match the new behavior; `metadata.version` bumped.
- The interrogation, its rules, and the verify step preserved verbatim in spirit.

**Non-Goals:**

- **Touching any other skill.** `arbor-auto-refine`, `arbor-auto-work`, `arbor-auto-developer`, `arbor-opsx-auto`, and `arbor-project-scaffold` are not modified, deleted, or moved by this change. Only `.claude/skills/arbor-auto-roadmap/SKILL.md` changes.
- **Scrubbing `arbor-auto-refine` references out of `arbor-auto-roadmap`.** See the decision below — this is deliberately deferred to roadmap item R2.
- **Migration tooling** for repos already using singular `docs/roadmap/` with refine-era semantics. Hand migration only, per the parent roadmap's non-goals.
- **Teaching `arbor-auto-work` to consume the new item reference.** That is roadmap item R3. This change only *documents* the format from the producer side.

## Decisions

**D1 — Delete the format branch outright rather than deprecate it.**
Step 1 (format interrogation), the Setup section, and step 8 (Milestones + tracking issue) are removed, not marked deprecated. Alternative considered: keep Milestones behind a flag. Rejected — a skill is a prompt, and every retained branch costs context and invites the model to take the dead path. With one consumer (`arbor-auto-work` via `arbor-auto-developer`) there is nothing to preserve compatibility with. The step numbering renumbers to close the gap so the "create a todo per step" instruction stays coherent.

**D2 — Plural `docs/roadmaps/`, with no compatibility read of the singular path.**
The skill only ever *writes*; it never reads an existing tree to decide where to put things. Adding "check for a legacy `docs/roadmap/` first" would introduce a branch that outlives the migration. Repos with the old directory rename it by hand.

**D3 — Existing `arbor-auto-refine` references stay in place for now.**
The current body names `arbor-auto-refine` in several places (the companion framing at the top, the non-goals rationale in the interrogation, the item-sizing note, and the guardrails). Removing them is R2's acceptance criterion — R2 deletes the skill *and* scrubs the references together, so the two never disagree. Scrubbing them here would leave the repo in a state where `arbor-auto-roadmap` denies the existence of a skill that is still installed and still running on a schedule. **Implementation rule: do not remove `arbor-auto-refine` mentions that survive the deleted sections; there is no task in `tasks.md` for it.** Only mentions that live *inside* removed content (the format branch, the `Roadmap:` line contract) disappear as collateral. What must change is any statement that assigns *checkbox-flipping and close-out* to refine — the checkbox semantics are being redefined here, so those specific claims are rewritten to the new "implemented, gated, and merged" model rather than left contradicting the rest of the file.

**D4 — The item reference is documented as an argument, not a line.**
`docs/roadmaps/<slug>.md#R<n>` is described as the string handed to `arbor-auto-work` (the shape the parent roadmap's R3 will accept as a `roadmap:` token). The producer-side contract this skill owns is: the slug is the roadmap filename, `R<n>` is the permanent item ID, and the pair uniquely identifies one line in one file. The skill documents the format and its stability guarantee; it does not document `arbor-auto-work`'s token syntax or flip mechanics, which belong to R3 and would go stale if duplicated here.

**D5 — Archival is documented as an outcome, not an action this skill performs.**
The skill states where a fully-checked roadmap ends up (`docs/roadmaps/archive/`) so an author knows the file's lifecycle and so a re-invocation does not treat an archived roadmap as live. It explicitly does not move files — that stays with whoever flips the last box, consistent with the preserved guardrail that this skill never flips its own checkboxes.

**D6 — Version bump to `1.3`, and a `description` written for routing.**
Existing versions run `1.0`→`1.2` in minor steps; `1.3` follows that convention. Alternative considered: `2.0` for the breaking format removal. Rejected — nothing in the repo consumes `metadata.version` as a compatibility signal, so the sequence is documentation, and the repo's own convention wins. The `description` must stop advertising the Milestones option and the refine hand-off (both gone from the body) because it is the routing text an agent reads when deciding whether to invoke the skill; a description describing removed behavior misroutes.

## Risks / Trade-offs

- **The skill will reference `arbor-auto-refine` while describing checkbox semantics refine does not implement** → Accepted and bounded by D3: the surviving references describe refine as a companion/consumer, and any claim that refine flips boxes is rewritten. The window closes at R2, which is in the same phase of the parent roadmap.
- **`arbor-auto-refine` looks for `docs/roadmap/` (singular) and will silently find no roadmaps at the new plural path** → Accepted. Refine is deleted in R2. Silent no-op is the safe failure mode here: under the new semantics refine flipping a box would mark unimplemented work as done, so *not* finding the files is strictly better than finding them.
- **`arbor-auto-work` does not yet accept the documented item reference, so the format is aspirational for one change** → Accepted; R3 implements the consumer. The reference format is deliberately trivial (path + `#` + ID) so there is no interface to get wrong.
- **Deleting the Milestones path is irreversible for any user who preferred it** → Accepted. Git history retains it, and the parent roadmap's non-goals rule out a GitHub-backed queue entirely.
- **Renumbering steps risks dropping a preserved rule during the edit** → Mitigated by making each preserved rule its own verifiable task in `tasks.md` and by the final read-back task that diffs old against new for anything lost.

## Migration Plan

Single-file edit, no rollout: rewrite `.claude/skills/arbor-auto-roadmap/SKILL.md`. Rollback is `git checkout` of that one path. Downstream repos with an existing singular `docs/roadmap/` rename the directory by hand and re-read their checkboxes under the new meaning; no tooling ships for this.

## Open Questions

None blocking. The consumer-side syntax for passing `docs/roadmaps/<slug>.md#R<n>` into `arbor-auto-work` is settled by R3 and is intentionally not pinned down here.
