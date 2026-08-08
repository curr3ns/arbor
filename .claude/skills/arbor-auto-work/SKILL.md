---
name: arbor-auto-work
description: Run the mandatory agentic work cycle for a slice of work — assign a work ID, branch, author and apply an OpenSpec change, gate on the project's verification command, archive, commit, push, and integrate. Use when starting or completing any non-trivial change. Accepts spec:/work:/gate:/archive: model tokens and forwards them to the lifecycle, plus an optional roadmap: item reference that this cycle closes out on commit. Defaults to autonomous; pass --interaction to run with approval prompts, or --pr to run autonomously but open a pull request instead of merging.
license: MIT
metadata:
  author: arbor
  version: "1.2"
---

# Arbor work cycle

The required process for all non-trivial work in a repo. It layers the
work-ID + branch conventions and the commit/push/integrate steps on top of the
`arbor-opsx-auto` OpenSpec lifecycle (propose → apply → gate → archive). Two
modes:

- **autonomous** (default): proceed through every step without prompts; merge to
  `main` at the end. Pass `--pr` to end by pushing and opening a pull request
  instead of merging — still no prompts.
- **interactive** (`--interaction`): ask for approval before applying and before
  archiving (both handled inside the lifecycle); open a pull request at the end
  instead of merging.

## Inputs

A short description of the slice of work, and optionally the type (`DEV` for
development — the default — or `INFRA` for infrastructure), mode (`--interaction`
or `--pr`), per-phase model tokens (`spec:`/`work:`/`gate:`/`archive:`, bare or
behind `--models`), and a roadmap item reference
(`roadmap:docs/roadmaps/<slug>.md#R<n>`, the format `arbor-auto-roadmap`
defines) naming the roadmap item this cycle is building. The model tokens are
not interpreted here — they are stripped from the description and forwarded to
`arbor-opsx-auto`, which owns the model defaults and parsing (see its **Model
selection** section). The roadmap reference is optional: omitting it runs the
cycle unchanged — no flip, no roadmap commit bullet, no error.

## Steps

You MUST create a todo per step and complete them in order.

0. **Split off model and roadmap tokens.** Set aside any
   `spec:`/`work:`/`gate:`/`archive:` tokens (bare or behind `--models`), the
   `--interaction`/`--pr` flags, and any `roadmap:` token. What remains is the
   work description used everywhere below. Keeping all of them out now ensures
   none leaks into the work-ID slug in steps 2–3. The `roadmap:` reference
   stays with this skill — unlike the model tokens, it is never forwarded to
   `arbor-opsx-auto` in step 4.

   If a `roadmap:` token was supplied, resolve and validate it now, before the
   branch is created in step 3: `docs/roadmaps/<slug>.md` must exist, it must
   contain an item with the given `R<n>`, and that item's box must be
   `- [ ]`. Each of the following is a hard error that stops the run — never
   create the file, append the item, fall back to another item, or downgrade
   any of them to a warning or a silent skip: the file does not exist (this
   includes a reference into an already-archived roadmap — resolve it as
   missing, never search `docs/roadmaps/archive/` for the item); the file
   exists but has no item with that `R<n>`; the item exists but its box is
   already `- [x]`.

1. **Determine the slice.** Restate the smallest shippable unit of work. If it's
   too big for one change, stop and split it.
2. **Assign the work ID.** Type is an **uppercase** `DEV` (default), `INFRA`, or
   another established uppercase type. The next number is one more than the
   highest existing ID of that type across `openspec/changes/` and
   `openspec/changes/archive/`:
   ```bash
   ls -d openspec/changes/*/ openspec/changes/archive/*/ 2>/dev/null \
     | grep -oE '[A-Z]+-[0-9]+' | sort -t- -k2 -n
   ```
   Form the change name `<TYPE>-<n>-<slug>`: uppercase type prefix, lowercase
   kebab-case slug (e.g. `DEV-4-add-cart`). The change name **is** the work ID.
3. **Create the branch** `feature|bugfix|hotfix/<id>-<slug>` (feature for
   features, bugfix for fixes, hotfix for hotfixes), e.g.
   `feature/DEV-4-add-cart`.
4. **Run the OpenSpec lifecycle.** Invoke the `arbor-opsx-auto` skill with the
   slice as the work description, the `<TYPE>-<n>-<slug>` change name from step 2,
   and the model tokens set aside in step 0 forwarded verbatim. In
   `--interaction` mode, pass `--interaction` so it asks for approval before apply
   and before archive. It proposes, applies, runs the project's gate, and
   archives the change on the current branch under the requested (or default)
   per-phase models, leaving everything uncommitted. The bar is a change that
   genuinely satisfies the requested slice to a production standard — the
   feature actually works, meets the spec's acceptance criteria, and follows the
   repo's conventions — not merely one that moves through the steps. **Read back
   its reported gate outcome** — in particular an environment-blocked stage and
   its reason, which step 5 must surface. A genuine gate failure or any incomplete
   task stops the lifecycle there; do not continue to commit.
5. **Commit.** If a valid `roadmap:` reference was supplied, flip the item
   before authoring the commit — reaching this step is itself the
   precondition, since a genuine gate failure or incomplete task already
   stopped the cycle at step 4. Re-confirm the target line is still
   `- [ ] **R<n>**`, then change only that marker to `- [x] **R<n>**`, leaving
   the item's text and wrapped continuation lines byte-identical. Then test
   the whole file: if no `- [ ] **R<m>**` line survives for any item `<m>` —
   not just the one you flipped — the roadmap is complete, so create
   `docs/roadmaps/archive/` if it isn't there yet and `git mv` the file into
   it; the flip already landed, so the archived copy carries the checked box.
   If any item is still unchecked, leave the file at
   `docs/roadmaps/<slug>.md`. Stage the flip and any move into the same
   commit as the work, on the same branch — no separate bookkeeping commit
   or push.

   Commit with a subject `{ticket} {short description}` (uppercase work ID,
   e.g. `DEV-4 add cart`), optionally followed by a blank line and `-` bullets
   for detail. Follow the repo's commit conventions if documented. If step 4
   reported an environment-blocked stage — which still reaches the flip and
   any archival above — add a bullet surfacing it, e.g. `- E2E skipped:
   environment-blocked (<reason>); not independently verified.` If a
   `roadmap:` reference was supplied, add `- Roadmap: <slug> R<n> complete`
   (`<slug>` is the roadmap filename without its `.md` extension); if the flip
   also archived the file, additionally add `- Roadmap <slug> complete;
   archived`. All three bullets are independent and may appear together in one
   commit body.
6. **Push** the branch.
7. **Integrate.** Autonomous: merge to `main` — unless `--pr` was passed, in
   which case push and open a pull request instead of merging. Interactive: open
   a pull request.

## Guardrails

- The gate runs inside `arbor-opsx-auto` (step 4); a genuine gate failure stops
  the cycle there and you never reach commit.
- The roadmap flip and any archival happen only because step 5 was reached —
  never as bookkeeping independent of the step 4 gate outcome.
- A gate stage may only be treated as skipped when it itself reports an
  environment-blocked outcome — never as a shortcut, and never for a genuine
  failure against infrastructure that did come up. When step 4 reports one, that
  skipped stage MUST leave a visible trace here (commit bullet, and PR/merge note
  if applicable) — never merge unverified changes silently.
- One change = one work ID = one branch. Keep them in sync.
