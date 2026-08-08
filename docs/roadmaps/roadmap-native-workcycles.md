# Roadmap-native workcycles

Make roadmaps the spine of the arbor loop rather than a planning artifact that
feeds a separate queue. A checked box changes meaning from "refined into the
backlog" to "implemented, gated, and merged," and everything else follows from
that inversion: the GitHub issue backlog disappears, `arbor-auto-refine` is
deleted, `arbor-auto-work` learns to close the item it just built, and
`arbor-auto-developer` reads `docs/roadmaps/*.md` directly as its work queue.
When every item in a roadmap is checked, the file migrates to
`docs/roadmaps/archive/`. The end state is four skills — `arbor-auto-roadmap`
plans, `arbor-auto-developer` burns down, `arbor-auto-work` builds and marks
done, `arbor-opsx-auto` runs the OpenSpec lifecycle underneath — and a system
that only ever builds what a human roadmapped.

## Non-goals

- **Replacing what `arbor-auto-refine` did beyond roadmaps.** Its static doc
  audit, its dynamic exploration against the running app, and its blocked-issue
  triage are deliberately dropped, not relocated. No agent finds bugs after
  this work.
- **Any GitHub issue backlog.** No `agent:backlog` queue, no `priority:*` or
  `type:*` labels, no queue cap, in any skill. Work that isn't on a roadmap has
  no automated home, by design.
- **A separate `/arbor-goal-roadmap` skill.** `/goal` folds into
  `arbor-auto-developer` as a foreground mode instead.
- **Changing `arbor-opsx-auto`.** It runs branch-local and leaves everything
  uncommitted, so it has no roadmap concern and is not touched.
- **Migration tooling for downstream projects.** Repos already using
  `docs/roadmap/` (singular) with refine-era checkbox semantics are migrated by
  hand; this roadmap ships no automated conversion.

## Phase 1: Retire refine and re-found the roadmap contract

- [x] **R1** Rewrite `arbor-auto-roadmap` as a files-only planning skill.
      Roadmaps are always `docs/roadmaps/<slug>.md`, completing to
      `docs/roadmaps/archive/`. Why: the GitHub Milestones format only existed
      to feed refine's issue-filing path, and with the roadmap becoming the
      queue itself there is one consumer and one format. Acceptance criteria:
      the format interrogation (current step 1) and the entire Milestones +
      pinned-tracking-issue branch are gone; the directory is plural
      `docs/roadmaps/` throughout; a checked box is documented as meaning
      "implemented, gated, and merged," never "refined"; the per-milestone
      ID-numbering rules collapse to the single file-scoped rule (`R<n>`
      sequential across the file, permanent, never reused or renumbered); the
      `Roadmap:` reference-line contract is replaced by an item-reference
      format `docs/roadmaps/<slug>.md#R<n>` documented as an argument passed to
      `arbor-auto-work` rather than a line in an issue body; the skill still
      never flips its own checkboxes and is still only ever human-invoked; the
      GitHub-only Setup section is removed.

- [x] **R2** Delete `arbor-auto-refine` and scrub it from
      `arbor-auto-roadmap`. Why: refine flips boxes at issue-filing time, which
      under R1's new semantics would mark unimplemented work as done — it has
      to go in the same phase that redefines the checkbox, not later.
      Acceptance criteria: `.claude/skills/arbor-auto-refine/` is removed;
      `install.sh` is confirmed to need no change (it already prunes dangling
      symlinks pointing into this repo's skills dir) or is fixed if that
      confirmation fails; no reference to `arbor-auto-refine` survives in
      `arbor-auto-roadmap`'s description or body. `arbor-auto-developer` still
      references refine at the end of this item — that is expected and is
      resolved by R4; note it rather than half-fixing it here.

## Phase 2: Close items from the work cycle

- [x] **R3** Teach `arbor-auto-work` to close the roadmap item it just built.
      Why: putting the flip in the work cycle means it rides in the same commit
      on the same branch as the work, so it lands atomically on merge, needs no
      separate bookkeeping push, has no push race to reconcile, and works
      identically for a scheduled agent and a human running the skill by hand.
      Acceptance criteria: a new optional input token
      `roadmap:docs/roadmaps/<slug>.md#R<n>` is stripped in step 0 alongside
      the model tokens, so it can never leak into the work-ID slug built in
      steps 2–3; inside step 5, before the commit, the referenced item is
      flipped to `- [x] **R<n>**` and — if every item in the file is now
      checked — the file is `git mv`d to `docs/roadmaps/archive/` in that same
      commit; the commit body gains a `- Roadmap: <slug> R<n> complete` bullet,
      plus a `- Roadmap <slug> complete; archived` bullet when it was the last
      item; a ref naming a missing file, a missing item, or an
      already-checked item is a hard error that stops the run rather than being
      silently ignored; a genuine gate failure never reaches the flip (step 4
      already stops the cycle); an environment-blocked stage still flips but
      carries the same visible trace step 5 already requires.

## Phase 3: Make the roadmap the queue

- [ ] **R4** Rewrite `arbor-auto-developer` to read `docs/roadmaps/*.md` as its
      work queue and merge to `main`. Why: with the checkbox meaning
      "implemented" and refine gone, the roadmap is already an ordered,
      deduped, human-authored backlog — a second queue in GitHub adds
      bookkeeping without adding information. Acceptance criteria: the
      `agent:backlog` queue, all label requirements, the queue cap, the
      `gh auth` setup step, the integration-branch setup step, the running PR,
      the entire P0/P1 PR-feedback path, and refine self-seeding are all
      removed; each cycle reads non-archived `docs/roadmaps/*.md` on `main`,
      walks roadmaps in filename order, and within the first roadmap holding an
      eligible item picks the earliest incomplete phase and its first unchecked
      item not carrying a blocked annotation; exactly one subagent is
      dispatched running `arbor-auto-work` autonomously with that item's text
      and its `roadmap:` ref, merging to `main`; no eligible item anywhere ends
      the run quietly, as does the absence of any roadmap; on gate failure one
      retry subagent runs with the failure output, and if that also fails an
      `<!-- blocked: <reason> -->` annotation is appended to the item's line and
      pushed to `main` as bookkeeping so later cycles skip it and one bad item
      cannot stall the roadmap; notifications fire on merge landed, item
      blocked after retry, and roadmap complete; the phases-are-strictly-
      sequential rule and the one-subagent-at-a-time rule survive; the skill
      still never authors roadmap content.

- [ ] **R5** Add a `--goal` foreground mode to `arbor-auto-developer`. Why: the
      cron cadence handles unattended burn-down, but a human who wants to watch
      a roadmap finish in one sitting currently has no path; `/goal`'s
      session-scoped Stop hook provides exactly that loop without a fourth
      skill. Acceptance criteria: `--goal` sets `/goal` with a condition naming
      the target roadmap — "Every item in `docs/roadmaps/<slug>.md` is checked
      off and the file has been migrated to `docs/roadmaps/archive/`" — then
      works items one at a time, relying on the Stop hook to keep the session
      going and auto-clear when the condition holds; the documented behavior
      notes `/goal` requires a trusted workspace and unrestricted hooks, and
      that when it is unavailable (`disableAllHooks` or
      `allowManagedHooksOnly`) the skill reports the reason and falls back to
      running cycles back-to-back in-session until no eligible item remains;
      the default remains one cycle per invocation, so the scheduled path is
      unaffected.

## Phase 4: Project scaffolding

- [ ] **R6** Give `arbor-project-scaffold` roadmap awareness. Why: a fresh
      project should land with the directory layout the rest of the loop
      expects, so the first `arbor-auto-roadmap` run has somewhere to write.
      Acceptance criteria: scaffolding creates `docs/roadmaps/` and
      `docs/roadmaps/archive/` with `.gitkeep` files; the skill names
      `arbor-auto-roadmap` as the natural next step after scaffolding; no new
      interrogation questions are added to scaffold's existing question set.
