## Context

This is a skills repo: the product is Markdown skill definitions at `.claude/skills/<name>/SKILL.md`. There is no build, no test suite, no `package.json`, and no gate command. "Implementation" means editing one Markdown file, and the bar is prose precise enough that a future agent following it literally does the right thing in every case the acceptance criteria name. Verification is reading the finished file back against those criteria plus greppable checks.

`.claude/skills/arbor-auto-developer/SKILL.md` is v2.0, 252 lines, rewritten last cycle by R4. Its shape today:

- **Frontmatter** — description built around the roadmap queue, one dispatch per run, and the scheduled single-cycle framing.
- **Framing paragraph** — a scheduled burn-down agent; each run is a single cycle; the cron cadence supplies the polling; the skill never loops internally.
- **`## The cycle`** — the `You MUST create a todo per step and complete them in order.` directive and six numbered steps: read the queue, select exactly one item, quiet idle, dispatch one subagent, success path, and the non-`shipped` retry-then-annotate path with its push race.
- **`## Subagent dispatch`** — self-contained prompt, item text verbatim, `roadmap:` ref, autonomous mode, `main` as the untouched default target, the `{ outcome, work_id, branch, note }` return, one subagent in flight.
- **`## Notifications`** — exactly three events, two suppressions stated as rules, graceful degradation.
- **`## Guardrails`** — strictly sequential phases; one subagent at a time; at most two attempts per item per run; one run = one cycle, no internal loop; repo-scoped maintainer identity; never author roadmap content; the blocked annotation as the single carved-out write.

All of that is correct and stays. R5 is additive: one flag, one new section, one mode-framing paragraph, a version bump, and a small number of surgical clarifications where R4's wording was written under the assumption that a run is a single item and now has to be read under a loop.

The environment facts the mode is built on were read out of the installed Claude Code binary and are not negotiable: `/goal <condition>` sets a **session-scoped Stop hook** and confirms with "A session-scoped Stop hook is now active with condition: …"; `/goal clear` stops early; `/goal active` shows the current goal; `/goal` fails in an untrusted workspace ("/goal is only available in trusted workspaces. Restart, accept the trust dialog, and try again.") and under restricted hooks ("/goal can't run while hooks are restricted (disableAllHooks or allowManagedHooksOnly is set in settings or by policy)."); and Stop hooks are REPL-only ("Prompt stop hooks are not yet supported outside REPL").

The mechanism matters for how the skill is written. A Stop hook does not give the skill a loop construct — it intercepts the skill's *attempt to stop* and puts the session back to work, re-evaluating the condition each time. So under `/goal` the skill body per turn is still exactly one cycle; the repetition belongs to the hook. That is a materially different control flow from the fallback, where there is no hook and the skill really does have to repeat cycles in-session. Both shapes have to be written, and they have to terminate identically.

## Goals / Non-Goals

**Goals:**

- A `--goal` foreground mode that sets `/goal` with a condition naming the target roadmap in exactly the required form, then works items one at a time to the roadmap's finish.
- Mode contrast made legible: a framing near the top and a dedicated section, not a flag in a list.
- `/goal`'s preconditions documented, its two named unavailability settings stated, and a fallback that reports the reason and runs cycles back-to-back in-session.
- One termination condition shared by both paths, with a written argument for why the loop cannot livelock — including the all-blocked roadmap, which terminates rather than retries.
- A stated, considered re-reading of "at most two attempts per item per run" under a loop that spans many items.
- The default unchanged at one cycle per invocation, so the scheduled path is untouched.
- Frontmatter `description` mentioning the mode; `metadata.version` `"2.0"` → `"2.1"`.

**Non-Goals:**

- **Re-litigating R4.** The walk, the strictly-sequential phase rule, the archive exclusion, the dispatch contract, the blocked-annotation path and its push race, the three notifications, and merging to `main` are settled. This change adds a mode on top of them and must not soften or contradict any of them.
- **A fourth skill or a new capability.** The parent roadmap names "a separate `/arbor-goal-roadmap` skill" as an explicit non-goal.
- **A fourth notification event.** Neither "goal set" nor "goal reached" earns one; the existing three already cover every real outcome of a goal run.
- **Interactive dispatch.** "Foreground" describes the human watching, not approval prompts. Subagents stay autonomous.
- **Multi-roadmap goal runs.** One goal run finishes one roadmap. Chaining is the human's next invocation.
- **Touching `arbor-auto-work`, `arbor-auto-roadmap`, `arbor-opsx-auto`, or `arbor-project-scaffold`,** creating `docs/roadmaps/archive/`, or flipping R5's own checkbox.

## Decisions

**D1 — Additive edit, not a rewrite; version `2.1`.**
R4 replaced the queue, the integration target, and the failure path, which is why it went to `2.0`. R5 threads one new concern through an intact structure, which is the pattern this repo has consistently marked with a minor bump (`arbor-auto-roadmap` 1.2 → 1.3 → 1.4, `arbor-auto-work` 1.1 → 1.2). `2.1` is the honest signal. Concretely: the frontmatter description gains a clause, a mode-framing paragraph joins the opening, one new `## Foreground goal mode (--goal)` section is added after `## The cycle`, and a small number of existing sentences are clarified in place. Nothing in `## The cycle`, `## Subagent dispatch`, or `## Notifications` changes meaning. Alternative considered: restructure the file around a mode dispatcher at the top with the cycle as a shared subroutine. Rejected — it would rewrite settled prose to serve a flag, and the file's default reading is the scheduled path, which should stay the thing you encounter first.

**D2 — Mode contrast is stated twice, at two altitudes, and never as a bullet in an options list.**
The two modes differ on the axis that matters most for an agent deciding what to do: who is watching and what ends the run. A cron tick is unattended, paced by an external scheduler, and ends after one item. A `--goal` run is human-invoked, paced by the work itself, and ends at a stated finish line. An agent that meets `--goal` as one entry in a list of flags will treat the modes as interchangeable and, on a scheduled tick, reach for a loop it should not have. So: a short **mode framing** near the top names both modes and states which one is the default, and a dedicated `## Foreground goal mode (--goal)` section holds the behavior. The framing must say the default in the same breath as naming the flag — "without `--goal`, one cycle per invocation" — so that the criterion-3 promise is visible where an agent forms its plan, not only in the guardrails.

**D3 — The `/goal` condition string is fixed, names one roadmap, and is set once.**
The condition is literally "Every item in `docs/roadmaps/<slug>.md` is checked off and the file has been migrated to `docs/roadmaps/archive/`" with `<slug>` substituted for the real slug. Two properties of that sentence are load-bearing. First, it names a *specific* roadmap, so the hook's evaluation is a fact about one file rather than an open-ended "keep working" — an open-ended condition is one that never clears. Second, it states the archival half explicitly, which is what makes the condition satisfiable at all: once the roadmap completes, `arbor-auto-work` has `git mv`d the file into `docs/roadmaps/archive/`, so a condition phrased only as "every item in `docs/roadmaps/<slug>.md` is checked" would be evaluated against a path that no longer exists. Naming the migration is what turns the file's disappearance from ambiguity into the success signal.

The skill sets the goal exactly once, at the start of the run, and never re-issues it with a different condition mid-session. Re-targeting mid-run would leave a human unable to say what "done" meant for the session they are watching.

**D4 — Target selection: argument if given, otherwise first-eligible by the existing walk; pinned for the run; re-derived from `/goal active` on resumption.**
`--goal` accepts an optional roadmap argument — a slug or a `docs/roadmaps/<slug>.md` path. If the human names one, that is the target, and if it does not exist among the non-archived roadmaps the run stops and says so rather than silently retargeting: a human who names a roadmap and gets a different one worked is worse off than one who gets an error. With no argument, the target is the **first roadmap holding an eligible item under the skill's existing filename-order walk** — the same selection R4 already specifies, evaluated once and then held. Reusing the existing walk means the no-argument case needs no new selection rule, only a statement that its *result* is pinned.

Pinning matters because the walk is evaluated against a moving `main`. If the target were re-derived every iteration, an item annotated blocked in an earlier roadmap, or a human's concurrent edit, could shift the walk onto a different file while the `/goal` condition still named the original — the skill would then be working roadmap B toward a condition about roadmap A, which can never clear. When the session resumes after a Stop-hook re-prompt, the skill therefore recovers its target from `/goal active` rather than re-running the walk. `/goal active` is the authoritative record of what this session committed to, and it survives the context the re-prompt does not.

Two degenerate cases resolve at the start: if no roadmap holds an eligible item at all, the skill does **not** set a goal — an already-satisfied or unsatisfiable condition is worse than no hook — it reports and exits on the same quiet path as a scheduled idle tick. If the named roadmap exists but holds no eligible item (fully blocked, or fully checked but somehow unarchived), the skill likewise reports and exits without setting a goal.

Alternative considered for the no-argument case: prompt the human to choose. Rejected — the mode is meant to be a one-liner a human types before walking away for an hour, and the first-eligible walk is the same answer the scheduled path would have produced anyway, which keeps the two modes consistent about *what gets worked next*.

**D5 — Under `/goal`, the loop belongs to the hook; the skill still runs exactly one cycle per turn.**
A Stop hook intercepts the attempt to stop and re-prompts, re-evaluating the condition each time. So the correct instruction is not "write a loop" but "run one cycle, then stop; the hook will bring you back." This is worth stating in the file because the alternative reading — set the goal *and* loop internally — produces a session that is both looping and being re-prompted, doubles the work per turn, and makes the one-subagent guardrail much easier to violate. Each turn re-reads the queue on `main` (cycle step 1 already requires this), which is exactly what makes a hook-driven repetition safe: the annotation or merge the previous turn pushed is visible to the next turn's walk, with no state carried in context.

The fallback is the opposite shape and must be written as such: with no hook, the skill repeats cycles back-to-back **in-session**, one after another, waiting for each to finish before starting the next.

**D6 — One termination condition, and a written argument for why the loop cannot livelock.**
Both paths stop when the target roadmap holds no eligible item — either because it is finished and archived, or because every unchecked item left carries a blocked annotation. The file must state the argument, not just the condition, because "keep going until the roadmap is done" is exactly the instruction an agent will pursue past the point where progress is possible:

Every iteration of the loop ends in one of two ways. Either the dispatched item **merges**, and the roadmap has one fewer unchecked item; or the item exhausts its two attempts, is annotated `<!-- blocked: … -->`, and the roadmap has one fewer *eligible* item — the annotation is pushed to `main`, so the next iteration's walk skips it. Both quantities are non-negative integers over a finite item set and both strictly decrease. The loop therefore reaches "no eligible item" in at most as many iterations as the roadmap has unchecked items. There is no third outcome that leaves both quantities unchanged, which is precisely why the two-attempt budget has to be read per item (D7): a budget that reset per item without the annotation surviving would let the same item be selected forever.

The all-blocked state is a **terminating** state, not a retry state, and the file says so in those words. R4 already established that blocked items wait for a human and that nothing re-attempts them automatically; the goal loop inherits that unchanged and must not invent a "try the blocked ones again now that we're here" pass.

**D7 — `/goal clear` is issued by the skill on the all-blocked terminal state.**
This is the one place where the `/goal` mechanism and the termination condition disagree, and it is the failure mode most likely to be missed. The two terminating states are not symmetric with respect to the hook. If the roadmap finishes and is archived, the condition holds, the hook clears itself, and the session ends — nothing to do. But if the loop terminates because every remaining unchecked item is blocked, the condition "every item … is checked off and the file has been migrated" is *false and will stay false*, so the Stop hook will keep re-prompting a session that has nothing left to do — an infinite loop of an agent being told to continue work it has correctly concluded is finished. The skill must therefore issue `/goal clear` itself before stopping in that state, and report which items are blocked and why. Same for the degenerate mid-run cases: if the target roadmap disappears for a reason other than archival, or the human's named roadmap turns out to hold nothing, clear the goal rather than leaving a live hook behind.

Alternative considered: phrase the condition so it is also satisfied by "or every remaining item is blocked." Rejected — it makes the condition depend on the hook's evaluator reasoning about annotations, turns a crisp factual check into a judgement call, and hides the blocked outcome from the human behind an apparently-clean "goal reached." An explicit `/goal clear` plus a report is louder and more honest.

**D8 — The two-attempt budget is per item; "don't move on" is a within-cycle rule.**
R4 wrote two rules under the assumption that a run is one item: "at most two attempts per item per run" and "never move on to a different item in its place in this run." Under a loop spanning many items, a literal reading of the first is ambiguous and a literal reading of the second would stop the goal run at its first blocked item. The file resolves both explicitly, in the direction that is both the natural reading and the one that makes the loop terminate:

- The budget is **per item** — one original plus one retry — and an item that exhausts it is annotated blocked, after which the walk skips it. So no item receives a third attempt within a goal run either, even though the run spans many cycles. The guardrail's force is unchanged; only the scope of the word "run" needed pinning down.
- "Never move on to a different item in its place" is a **within-cycle** rule: a cycle that fails does not chain into another item. The goal loop reaches the next item by *starting a new cycle*, whose walk re-reads `main` and therefore sees the annotation. That is a different thing from a failed cycle picking a replacement, and the distinction is what keeps the scheduled path's "one run = one cycle" true while letting the goal run continue.

As belt and braces, the goal loop also keeps a **session-local record of items it has exhausted this run** and treats them as ineligible for the remainder of the run. This costs one sentence and removes the loop's dependence on the annotation push having landed: R4's race procedure legitimately *drops* the annotation when the item has since been checked or already annotated by another actor, and while both of those outcomes happen to leave the item ineligible anyway, a termination argument that rests on a push succeeding is weaker than one that does not.

**D9 — "One run = one cycle" is scoped, not weakened.**
The guardrail as written says "Do not loop internally; exit as soon as the item is handled … and let the scheduler bring you back." That is exactly right for the default and exactly wrong as an unqualified statement once `--goal` exists. The fix is to scope it — it governs the default, scheduled invocation — rather than to soften it into "usually." An agent reading a softened guardrail will feel licensed to loop on a cron tick; an agent reading a scoped one will not, because the scope names the condition under which looping is permitted (`--goal` was passed) and that condition is checkable. The same treatment applies to the framing paragraph's "this skill never loops internally," which becomes a statement about the default path with the goal mode named as the exception.

This is the one place where existing R4 prose has to change meaning, and it is a scoping, not a reversal: on the scheduled path every one of these sentences remains true word for word.

**D10 — The one-subagent guardrail is restated inside the goal section, not merely inherited.**
"Works items one at a time" is the criterion's phrase and it is doing precise work: the same single dispatch per cycle, repeated. Not two subagents in flight, not a batch dispatch, not "one at a time but start the next while the last finishes." Inheriting the guardrail from the Guardrails section would be technically sufficient and practically insufficient — an agent that has just been told to finish a whole roadmap in one sitting has an obvious efficiency idea, and the place it will act on it is the goal section. So the goal section states it again in its own terms: exactly one subagent in flight at any moment across the entire goal run, retries included, and each cycle completes fully — dispatch, verify, notify, or annotate — before the next begins.

For the same reason the goal section restates that dispatch stays autonomous. "Foreground" is about the human watching the session, not about approval prompts; subagents still run `arbor-auto-work` in its default mode with no `--interaction` and no `--pr`. A reader who takes "foreground" to mean "interactive" would add prompts to a mode whose whole point is watching work happen unattended-but-present.

**D11 — Report-and-fall-back, with the reason named.**
When `/goal` fails, the skill states which of the three reasons applied — untrusted workspace, restricted hooks (`disableAllHooks` or `allowManagedHooksOnly`, named individually because those are the settings a human will grep their config for), or a non-REPL invocation where Stop hooks are unsupported — and then proceeds with the fallback rather than aborting. Aborting would be defensible but unhelpful: the fallback delivers the same outcome by a different mechanism, and the only thing lost is the hook's re-prompting, which matters less in a session a human is already watching. Reporting the reason is what makes the difference actionable: two of the three causes are one settings change away from being fixed.

The report is prose in the session, not a `PushNotification`. The notification set stays at three (D12), and a human who just typed `--goal` is by construction present to read the response.

**D12 — No new notification event, and no change to the existing three.**
Merge landed, item blocked after retry, roadmap complete — those already cover a goal run completely. A goal run that succeeds ends with roadmap-complete; one that terminates on all-blocked ends with the item-blocked notification for the last item it blocked. "Goal set" is a dispatch-shaped event, which R4 suppressed for good reason. "Goal reached" would duplicate roadmap-complete. Adding either would also break the existing spec scenario that requires no fourth trigger. The per-cycle notifications do fire once per item, which in a long goal run means several — accepted, because they are the durable record of what a run did, and the human can read them as a progress log.

**D13 — Completion handoff: one goal run, one roadmap.**
When the target completes while other roadmaps still hold eligible items, the run ends — the condition held, the hook cleared — and the skill reports the remaining roadmaps and the invocation that would continue with the next one. It does not roll onto another roadmap. The condition names one `<slug>`; continuing past it would mean either working outside a satisfied goal (the hook is gone, so nothing is driving it) or re-issuing `/goal` with a new condition, which D3 rules out. There is also a human-factors argument: a mode whose stopping point is "the roadmap you named is finished" is predictable, and one whose stopping point is "all roadmaps are finished" is an open-ended commitment a human did not make when they typed one command.

## Risks / Trade-offs

- **The loop spins forever on an all-blocked roadmap, re-attempting blocked items** → Mitigated by D6 and D8: the all-blocked state is written as a terminating state in those words, the annotation is what makes an item ineligible on the next walk, the budget is pinned as per-item, and a session-local exhausted-item set makes termination independent of the annotation push landing.
- **The `/goal` Stop hook keeps re-prompting an empty session after an all-blocked termination, because the condition can never hold** → Mitigated by D7: the skill issues `/goal clear` itself in that state and reports the blocked items. This is the highest-value single sentence in the change and a task greps for it.
- **The skill sets `/goal` and *also* loops internally, doubling the work per turn and putting two subagents in flight** → Mitigated by D5 and D10: under `/goal` the loop belongs to the hook and the skill runs exactly one cycle per turn; the in-session repetition is written only into the fallback path; and the one-subagent rule is restated inside the goal section as applying across the entire run.
- **The goal condition is written open-endedly ("until the roadmaps are done") and never clears** → Mitigated by D3: the condition string is fixed verbatim, names one `<slug>`, and includes the archival clause that makes it satisfiable.
- **The target roadmap drifts mid-run and the condition becomes unreachable** → Mitigated by D4: the target is resolved once and pinned, and on resumption is recovered from `/goal active` rather than re-derived from a walk against a moved `main`.
- **`--goal` leaks into the scheduled path, or the default silently becomes a loop** → Mitigated by D2 and D9: the mode framing states the default in the same breath as the flag, the goal behavior is quarantined in its own section, and the "one run = one cycle" guardrail is scoped to the default rather than softened. A task verifies the default is still one cycle per invocation.
- **Scoping "one run = one cycle" gets over-applied and weakens the scheduled guarantee** → Mitigated by D9: the change is a scope qualifier naming an explicit, checkable condition (`--goal` was passed); every one of those sentences remains true word for word on the scheduled path, and a task re-reads them under that assumption.
- **"Foreground" is read as "interactive" and approval prompts get added to dispatch** → Mitigated by D10: the goal section restates that dispatch stays autonomous with no `--interaction` and no `--pr`.
- **The fallback quietly diverges from the `/goal` path — different stopping point, different budget, different guardrails** → Mitigated by D6: both paths are written against one termination condition, and the fallback is described as "the same cycles, back-to-back, in-session," not as a second algorithm.
- **`/goal`'s failure is treated as a fatal error and the run aborts** → Mitigated by D11: the failure is reported with its reason and the fallback proceeds.
- **The change re-litigates R4 — rewording the walk, the annotation path, or the notifications while "in there anyway"** → Mitigated by an explicit non-goal, a scope requirement, and a task that diffs the finished file and requires every change outside the additive surface to be a D9 scoping or the version bump.
- **A fourth notification appears because a goal run feels like it deserves one** → Mitigated by D12 and a task that re-counts the notification triggers at exactly three.
- **A `--goal` run lands many autonomous merges on `main` in one sitting** → Accepted, and it is the point of the mode. The per-merge blast radius is unchanged — the gate inside `arbor-auto-work` is still the boundary, one subagent still runs at a time, and the work still comes only from a human-authored roadmap. What changes is rate, and the mode is human-invoked precisely so a human is present at that rate.
- **A human runs `--goal` in a non-REPL context and gets the fallback without understanding why** → Mitigated by D11's named reason; the REPL-only limitation is stated in the file alongside the two settings.

## Migration Plan

Single-file additive edit; no rollout, no data migration, nothing to deploy. Rollback is `git checkout` of `.claude/skills/arbor-auto-developer/SKILL.md`. Downstream repos pick it up the next time `install.sh` refreshes their skill symlinks — skills are symlinked, not copied, so there is nothing to version-pin.

There is no operational discontinuity: existing scheduled invocations pass no `--goal` and behave exactly as they did under v2.0. Any repo running the skill on a cron needs no change. The new mode is opt-in per invocation and leaves no persistent state behind — the Stop hook is session-scoped and clears either on the condition holding or on the skill's own `/goal clear`.

## Open Questions

None blocking. One item is deliberately deferred: `docs/roadmaps/archive/` existing from the start in freshly scaffolded projects is R6's, and `arbor-auto-work` already creates the directory on demand at first archival, so a goal run whose roadmap completes works correctly without it.
