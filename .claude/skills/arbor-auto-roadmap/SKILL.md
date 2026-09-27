---
name: arbor-auto-roadmap
description: Interrogates the user to build a multi-phase product roadmap, then files it to the project's roadmap destination — Markdown files under docs/roadmaps/ by default (one file per roadmap, one checkbox per item), or GitHub issues (an epic plus one issue per item), or Jira (an epic plus one story per item). The destination is recorded once per repo in .arbor/config.json; when no decision has been recorded yet, the skill asks the user at invocation. Use when planning or re-planning product direction beyond a single slice of work: phases, themes, sequencing, non-goals. Defines the docs/roadmaps/<slug>.md#R<n> item-reference format, passed as an argument to arbor-auto-work to identify which item a work cycle is building — a box is checked only once that item has been implemented, gated, and merged. Purely user-invoked when there's planning to do — never on a timer, and never invoked automatically by another skill.
license: MIT
metadata:
  author: arbor
  version: "1.5"
---

# Arbor auto-roadmap

This skill is the human-invoked planning front end. It sits outside the
cadence of `arbor-auto-developer`'s scheduled work cycle and is never invoked
by that cycle — it only ever runs because a human invoked it directly when
there's planning to do. It interrogates whoever is present via
`AskUserQuestion`, produces one roadmap, files it to the project's roadmap
destination, and stops.

The destination is one of three, recorded once per repo (see **Destination**):

| Destination | What gets written                                          | Who works it                                           |
| ----------- | ---------------------------------------------------------- | ------------------------------------------------------ |
| `files`     | `docs/roadmaps/<slug>.md`, one checkbox per item (default) | `arbor-auto-developer`'s roadmap queue                 |
| `github`    | one `epic` issue plus one issue per item                   | `arbor-auto-developer`'s issue queue                   |
| `jira`      | one Epic plus one Story per item, in a named Jira project  | `arbor-auto-developer`'s issue queue, on Jira          |

`arbor-auto-work` builds an item and marks it done; this skill polls nothing
itself, and never marks done an item it filed — a roadmap box is checked, or
an issue closed, only once that item has been implemented, gated, and merged.

**Generate nothing until the recap in step 6 is approved** — same rule as
`arbor-project-scaffold`. That includes the destination record: the decision
is held in the session until then.

## Destination

The repo's decision lives in `.arbor/config.json`, committed alongside the
code so every contributor and every later run files to the same place:

```json
{
  "roadmap": {
    "destination": "files"
  }
}
```

`destination` is `files`, `github`, or `jira`. The `jira` destination also
carries `"jira": { "project": "<KEY>", "itemType": "Story" }` beside it
(`itemType` defaults to `Story`; an optional `startTransition`, default
`In Progress`, names the workflow transition `arbor-auto-work` moves an issue
through when it claims it, and an optional `doneTransition`, default `Done`,
the one it closes an issue with).
`arbor-auto-developer` reads this record to decide which issue tracker it
works, and `arbor-auto-work` reads the project key for `jira:next`. Other top-level keys in the file belong to
other tools — read and rewrite only `roadmap`.

A `destination:<files|github|jira>` argument on invocation overrides the
recorded value for this run and, once the recap is approved, replaces the
record.

## Phase 1 — Interrogate

You MUST create a todo per step and complete them in order. One topic per
question (`AskUserQuestion` where multiple-choice fits).

1. **Destination.** Resolve where this roadmap will be filed, before asking
   anything about its content:

   - A `destination:` argument wins.
   - Otherwise read `roadmap.destination` from `.arbor/config.json`. If it is
     present and valid, use it and say so in one line ("Filing to GitHub
     issues, as recorded in `.arbor/config.json`") — do not ask again.
   - Otherwise no decision has been made: ask with `AskUserQuestion`,
     offering **Roadmap files in docs/roadmaps/ (Recommended)**, **GitHub
     issues**, and **Jira**. Say in each option's description who works the
     result (the table above) — every destination feeds
     `arbor-auto-developer`, and choosing Jira makes the Jira project the
     repo's issue tracker in place of GitHub issues. For Jira, follow up for
     the project key and the issue type items should use (default `Story`).

   Then check the destination is usable, and stop at the first failure:

   - `files` — nothing to check; `docs/roadmaps/` is created if missing.
   - `github` — `gh auth status` succeeds and
     `gh repo view --json hasIssuesEnabled` reports `true`.
   - `jira` — a way to create issues exists: an Atlassian/Jira MCP server's
     create-issue tool, or else the `jira` CLI (`jira me` succeeds). Confirm
     the project key resolves.

   On a failure, tell the user what is missing and ask whether to fix it and
   retry, or file to `files` instead. Never silently switch destinations.

2. **Name and vision.** A short roadmap name (becomes the slug — the file
   name, or the `roadmap:<slug>` label) and a one-paragraph statement of the
   outcome and timeframe this roadmap covers.
3. **Non-goals.** What this roadmap explicitly does not cover — the roadmap
   is the only place that exclusion gets written down, and writing it down is
   what stops scope from being quietly re-expanded on a later planning pass.
4. **Phases.** Names and sequence — a roadmap is at least one phase, usually
   two to five. Phases are strictly ordered: later phases don't start until
   the earlier one's items are all done (see **Guardrails**).
5. **Items per phase.** For each phase, the shippable slices that make it up.
   Phrase each like a backlog issue: a "why" plus acceptance criteria, sized
   like a single work cycle — one roadmap item becomes one
   `arbor-auto-work` cycle: one branch, one gate, one merge. Each criterion
   is one checkable statement — an input and an output, a visible behaviour,
   an error case — because on the `github` destination it becomes the intent
   gate's contract verbatim. An item too big to phrase that way should become
   two items.
6. **Recap.** Restate the destination, name, vision, non-goals, and every
   phase with its items, and get an explicit go before writing anything.

## Phase 2 — Generate

7. **Record the destination.** If step 1 asked the user, or a
   `destination:` argument differed from the record, write
   `roadmap` into `.arbor/config.json` (creating `.arbor/` if needed and
   preserving every other key). If the record already matched, leave the file
   untouched.

8. **File the roadmap** to the destination.

   **`files`** — create `docs/roadmaps/<slug>.md`:

   ```markdown
   # <Roadmap name>

   <vision paragraph>

   ## Non-goals
   - <item>

   ## Phase 1: <phase name>
   - [ ] **R1** <item — why + acceptance criteria>
   - [ ] **R2** <item>

   ## Phase 2: <phase name>
   - [ ] **R3** <item>
   ```

   IDs (`R<n>`) are sequential across the whole file, assigned once, and never
   reused or renumbered — if an item is dropped later, delete its line and
   leave the number retired; the next new item still takes max-used + 1.

   **`github`** — create any missing labels first (`gh label list` to check),
   never recolouring or redescribing an existing one:

   ```bash
   gh label create "epic"            -c "#3e4b9e" -d "Umbrella/tracking issue; never built directly"
   gh label create "roadmap:<slug>"  -c "#c5def5" -d "<Roadmap name>"
   gh label create "phase:<n>"       -c "#ededed" -d "Roadmap phase <n>"
   ```

   Then create one issue per item, **phase by phase and in item order**, one
   `gh issue create` at a time so each gets a later `createdAt` than the one
   before. `arbor-auto-developer` works unlabelled issues oldest first, so
   filing order is what carries the phase sequence onto the issue queue. Do
   not add `p0`/`p1`/`p2` — priority is the developer's call, and a priority
   label on a later-phase issue would pull it ahead of the earlier phase.
   Label each `roadmap:<slug>` and `phase:<n>`; the body follows the repo's
   feature template:

   ```markdown
   ### Problem
   <why>

   ### Acceptance criteria
   - [ ] <checkable statement>
   - [ ] <checkable statement>

   ### Non-goals
   <roadmap non-goals that bear on this item, if any>

   Part of the <Roadmap name> roadmap — phase <n>: <phase name>.
   ```

   Last, create the umbrella issue `Roadmap: <Roadmap name>`, labelled `epic`
   and `roadmap:<slug>`, carrying the vision, the non-goals, and each phase as
   a task list of its issues (`- [ ] #<n>`) — GitHub ticks those as the issues
   close. Creating it last means it can link every item; the `epic` label
   keeps it out of the work queue regardless of its age.

   **`jira`** — use the Jira MCP server's tools if one is connected,
   otherwise the `jira` CLI. Create the Epic first
   (`<Roadmap name>`, vision and non-goals in its description), then one
   issue of the recorded `itemType` per item, phase by phase and in item
   order, each parented to the Epic, labelled `roadmap-<slug>` and
   `phase-<n>` (Jira labels cannot contain spaces or colons), with the why
   as its description and the acceptance criteria as a checklist beneath it.
   For example, with the CLI:

   ```bash
   jira issue create -t Epic -s "<Roadmap name>" -b "<vision + non-goals>" --no-input
   jira issue create -t "<itemType>" -P <EPIC-KEY> -s "<item title>" \
     -b "<why + acceptance criteria>" -l roadmap-<slug> -l phase-<n> --no-input
   ```

   If a create fails partway, stop, report exactly which items were filed
   (with their keys or numbers) and which were not, and do not retry blindly
   — a re-run would duplicate what already landed.

9. **Verify.** Read back what was filed and show it to the user before
   ending the run — the roadmap file; `gh issue list --label
   "roadmap:<slug>" --state all` plus the epic; or the Epic's child issues in
   Jira. Every item from the recap must be present exactly once. A roadmap
   only this skill produced and no one reviewed is not done.

## Item reference

On the `files` destination, a roadmap item is addressed as
`docs/roadmaps/<slug>.md#R<n>` — the roadmap file's slug plus the item's
permanent ID. This is the string handed to `arbor-auto-work` as an argument,
to tell it which item the work cycle is building; it is not a line written
into a GitHub issue body.

A checked box (`- [x] **R<n>**`) means the item has been implemented, gated,
and merged — never "refined," "filed," or "queued." An unchecked box means
the work has not yet landed.

When every item in a roadmap is checked, the file moves to
`docs/roadmaps/archive/`. This skill does not perform that move; whoever
flips the roadmap's last box does.

On the `github` destination the issue number is the reference —
`arbor-auto-work issue:<n>` — and a closed issue is the checked box. On
`jira` the issue key is the reference — `arbor-auto-work jira:<KEY-n>` — and
an issue transitioned to Done is the checked box. The Epic is an Epic issue
type, which the work queue never selects.

## Guardrails

- No files created and nothing filed before the step 6 recap is approved.
- Ask for the destination only when no decision is recorded and none was
  passed as an argument — a recorded decision is never re-asked.
- Phases are strictly sequential: only the earliest phase that still has an
  unfinished item is eligible for work — unfinished meaning not yet
  implemented and merged — never a later phase while an earlier one is
  incomplete. The roadmap queue enforces this; on GitHub and Jira it rests on
  filing order, so a developer who adds priority labels — or raises a Jira
  issue's Priority — takes over the sequencing.
- Item IDs are permanent once written — never renumbered, never reused after
  an item is dropped.
- Multiple concurrent roadmaps (several `docs/roadmaps/*.md` files, or
  several `roadmap:<slug>` labels / Epics) are fine; each is tracked and
  completed independently.
- This skill only ever writes a *new* roadmap or extends one it's re-invoked
  on — on GitHub or Jira, extending means filing new items and appending them
  to the epic, never editing, re-scoping, or closing an existing issue. It
  never flips a checkbox and never archives or closes out a roadmap itself.
  No other skill ever invokes this skill automatically; it is only ever run
  by a human.
