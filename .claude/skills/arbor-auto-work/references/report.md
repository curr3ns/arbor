# The implementation report

Every cycle ends with a templated summary page served on localhost: the record
a reviewer reads before (in `--manual`) or after (by default) the work is
committed. Never hand-write the HTML: fill the data file, run the generator.

`<skill>` below is this skill's directory (`~/.claude/skills/arbor-auto-work`).
`<work dir>` is the workspace root in workspace mode, otherwise
`~/.arbor-reports/<ID>/work/` (outside the repo, so nothing here is ever
committed).

## Collect throughout the run

From the moment the branch or workspace exists, keep a running data file at
`<work dir>/report.json` and append to it as things happen. The orchestrator
updates it; subagents report facts back to be recorded. Record hiccups the
moment they occur (failed builds, flaky tests, MCP/IDE fallbacks, spec
corrections, review findings, retries) with what happened and how it was
resolved.

## Schema

All fields optional except `ticket` and `workspace`. `ticket` is the work ID
(the ticket key when there is one).

```json
{
  "ticket": "PROJ-123", "url": "<ticket link>", "title": "<ticket summary>",
  "workspace": "<work dir>",
  "profile": "<path of the project profile used, if any>",
  "vcs": "<VCS mapping name (~/.claude/arbor/providers/vcs/<name>.json) or path; required>",
  "reportUrl": "<optional page URL template with {ticket} and {port}, e.g. a local proxy; default http://localhost:{port}/{ticket}/>",
  "testManagement": "<test-management mapping name or path; only when its skill is in the session>",
  "manualTestsForbid": ["<project environment names and hosts the manual-test lint must flag; from the profile>"],
  "summary": "<what was asked and what was done, a few sentences>",
  "analysis": "<full ticket analysis: description, expectations, links, assumptions>",
  "acceptanceCriteria": ["<one per criterion>"],
  "specFile": "<work dir>/spec.md",
  "agents": [{"name": "planner", "model": "opus", "task": "<what it was asked>", "result": "<its full report, as received>"}],
  "artifacts": ["<work dir>/<repo>/openspec/changes/<change> (file or directory; contents are embedded)"],
  "commitMessage": "<string, or an object keyed by repo name>",
  "repos": [{"name": "<repo>", "path": "<work dir>/<repo> or the repo path", "branch": "feature/PROJ-123-slug", "baseBranch": "main", "pushed": false}],
  "tests": [{"kind": "Unit|Automation|Automation (full suite)|Browser (Claude in Chrome)|API", "status": "passed|failed|skipped|n/a", "summary": "<one line: the result>", "points": ["<optional short bullets; max ~5>"], "command": "<the exact command run; required so Rerun can repeat it>", "newTests": 0, "ranAt": "<YYYY-MM-DD HH:MM>", "stale": "<optional: why this row was not re-run>"}],
  "review": {"cycles": 2, "outcome": "clean", "notes": ["<finding and fix>"]},
  "hiccups": [{"title": "", "detail": "", "resolution": ""}],
  "manualTests": {"intro": "This verifies PROJ-123.", "whatChanged": "<2-4 plain sentences about behavior, not code>", "tests": [{"title": "<what is proven>", "ticket": "<optional>", "steps": ["<short imperative sentence, one action each; do not number>"], "expected": ["<observable outcome>"], "before": "<optional: old behavior>", "notes": ["<optional>"]}], "automated": {"text": "<where the specs live and what they cover>", "command": "<exact run command>", "setup": "<setup caveat>"}},
  "evidence": [{"file": "<work dir>/evidence/<name>.jpg", "caption": "<what the screenshot shows, with ids>", "test": "<optional: the test row kind it belongs to>"}],
  "explanations": [{"repo": "<repo>", "file": "<repo-relative path as in the diff>", "match": "<substring of the target hunk, e.g. a method name; omit for a file-level explanation>", "title": "<=70 chars, what changed", "why": "<1-2 short sentences: the problem and the choice>", "points": ["<optional short bullets, <=100 chars each, max 4>"], "example": "<optional text block: a concrete input -> result>", "alternatives": "<optional>", "risks": "<optional: edge cases, test coverage>"}],
  "setup": ["<how the local run was set up: services, config, test data roots>"],
  "followups": ["<anything left for the user>"]
}
```

`newTests` is how many tests this cycle added to the suite; it shows as `(+N)`
on the Tests and Passed tiles.

The report must let the user see everything from the session: the ticket
analysis, the spec, every subagent's task and full result (record each as it
returns, in `agents`), review findings, hiccups, and any OpenSpec or other
artifacts. Save the plan to `<work dir>/spec.md` and point `specFile` at it.

**Markdown renders.** The spec, every agent result and any `.md` artifact are
rendered as markdown on the Plan & agents tab, each with a Rendered / Raw
toggle, so write specs and agent reports as normal markdown. In the Changes tab
every changed `.md` file gets a Diff / Preview switch. The renderer is
`md_to_html` in `report/build_report.py` (server-side, escaped output, no
external libraries); images, raw HTML and footnotes show as plain text.

## Test management

When the project keeps test cases in a test-management system, the page can
publish to it. Set `testManagement` to that system's mapping (a name under
`~/.claude/arbor/providers/tests/`, or a path) **only when the skill the
mapping names is in this session's skill list**. Otherwise leave it out: the
page then shows no test-management badges, bars or buttons, and the server
refuses those actions. Never enable it on a guess.

The mapping is JSON: `label` (the name shown on the page), `skill` (the skill
the headless job invokes), `helper` and `helperUsage` (a script that makes the
system's API calls and adds authentication itself), `tokenEnv` (the variable in
`~/.zshrc` the helper reads), `keyPattern` (a regex whose one group captures a
published test's key from its title), `keyFormat` (how a key is written into a
title, `{key}` the placeholder), and optionally `specPattern` (which changed
files are automated specs) and `testPattern` (a regex whose second group is a
test's title). Its contract is `test_mgmt` in `report/build_report.py`. A
mapping that does not exist yet is built like any provider mapping
(`SKILL.md`'s `## Providers`) from the system's skill and saved there.

When it is on, each automated spec in the Changes tab carries a **<label> n/m**
badge (green when every test's title carries a key, amber otherwise, also shown
in the file tree). A bar at the top of the file offers **Publish all
unpublished** (runs the mapping's skill headlessly via `claude -p`) and
**Create manual test cases** (from `manualTests`, else `acceptanceCriteria`);
under each test's definition line a row offers **Publish this test**. The
headless job may use `Skill`, `Edit`, `Read`, `Glob`, `Grep`, `jq` and the
mapping's helper only. **Never let a headless command contain the token
variable** (the harness blocks unresolved variables): every API call goes
through the helper. A publish counts as failed when no new key reached a spec,
since `claude -p` exits 0 even when it could not do the work. When a publish
succeeds for a spec that is already committed, the server **stages a commit**
in `pendingCommits` (`<ID> Link automation tests to <label> (<keys>)`), shown
as a chip next to **Commit & push**; nothing is committed until the user
presses that button, which creates each staged commit (limited to its own
files) first. `ARBOR_REPORT_DRY_RUN=1` makes the publishing and Rerun buttons
log their command instead of running it.

## Manual tests (required)

Every report has `manualTests` in the house style of
`references/manual-tests-example.md` (or the example the profile names): copy
its structure, not its content. "This verifies ..." intro, **WHAT CHANGED** in
2-4 plain sentences of behavior, then one test per scenario in this order:
reproduce the original bug, the other acceptance criteria and edge/race cases,
access/permissions, removed or admin features, **Regression** last.

**Manual tests never name an environment.** No environment names, no hostnames
or URLs with an environment in them, no ports, no framework profiles or `-D`
flags, no local-stack or startup steps. Refer to tools generically and let the
tester use whichever environment they are testing; the automated block says
"point the run at the environment you are testing". Local-run details belong in
`setup`. The generator lints `manualTests` for generic environment words plus
the report's `manualTestsForbid` list and shows a warning on the page (and on
stderr) until they are removed.

Steps are short imperative sentences (the page numbers them); test data is built
fresh (never ids quoted in the ticket; say so); the last item is `expected` as
observable bullets (what the user sees, a status code, a log line present or
absent, never "works correctly"); add `before` with the old behavior where
known; finish with `automated` (spec path, run command, setup caveat). The tab
renders per-step checkboxes, a **Copy rich text** button (keeps its
formatting when pasted into a ticket system's editor), **Copy markdown**, and a
**Copy** button per test.

## Test rows

**Stat tiles, not prose.** The page renders tiles (Build, Tests, Passed, Failed,
Skipped, Runs passed) and a pass/skip/fail bar parsed from `summary`; when tiles
show, `summary` and `points` are hidden and the row is tiles plus `command`. So
write `summary` as the full-suite counts (`11,519 tests, 0 failures, 0 errors,
124 skipped`, `BUILD SUCCESSFUL`) and set `newTests`. Every category reports its
**whole** suite totals, never only the new specs (`5 of 5 runs` is the fallback
for rows without counts and is not acceptable for Automation). Other rows may
add `metrics: [{"label","value","tone":"ok|warn|bad|neutral"}]`.

`summary` is one line with the result; specifics go in `points` (one fact each,
identifiers in backticks); the exact command in `command`. Never a paragraph.
A row whose `kind` matches an evidence item's `test` label gets an "N
screenshots" chip. Failed or skipped rows say why in `summary` and name the
exact blocker in `points`. Never write `passed` for a row whose run was not
executed in this session.

**Give every row a `command`** and write `ranAt` when you run it, so Rerun can
repeat it.

## Evidence screenshots

Save every browser screenshot taken as evidence in `<work dir>/evidence/`
(outside the repos) and list it in `evidence` with a one-line caption saying
what it proves and which ids are shown (proof first, setup and superseded
attempts last). The generator copies the images next to the page so they
survive a deleted workspace and shows them as a gallery on the Verification tab.
Without `evidence` it picks up every image in `<work dir>/evidence/` with
captions from the file names, so always write captions.

## Explanations (required)

Every changed file needs at least one file-level entry (no `match`); files with
several independent hunks (source and test files) get one entry per hunk, with
a `match` that occurs in exactly that hunk. Build them from the implementers'
Decision notes, the plan, and the review and hiccup fixes; mark anything not
recorded as "Inferred: ...". Large new files need one file-level entry. The page
shows **Why this change?** on each explained hunk, **Why?** on each file header,
and **Explain all**. The generator prints `warning: explanation match not
found` on stderr for a `match` that hits no hunk (it then falls back to file
level): fix those before showing the page.

Style — the reviewer reads these in a small panel: `why` is one or two short
sentences. Detail goes in `points` (max 4, each under 100 characters, one idea
each). Whenever the logic is about data or behavior, add an `example` with
concrete values (input and result, or before/after). `alternatives` and `risks`
are one line or a short list, only when real. For tests, list the scenarios
covered as bullets. Over about 80 words in total: split into two entries on
different hunks, or cut.

The generator and server reach the repository only through the VCS mapping
the report's `vcs` field names (its contract is in `report/vcs.py`). Diffs,
file counts and commit lists are computed from the repository by the
generator (from the point the branch left `<baseBranch>`, plus uncommitted and
untracked changes); never paste them in. Never put passwords or tokens in `report.json`.

## Generate and serve

```bash
python3 <skill>/report/build_report.py <work dir>/report.json
```

It renders the ticket page to `~/.arbor-reports/<ID>/index.html` (plus a copy
of `report.json`) from `report/templates/`, then updates the **all-tickets
index** at `~/.arbor-reports/index.html` (one row per ticket, newest first). One
background server (`report/server.py`, bound to `127.0.0.1`, always port 8766,
reused if already running) serves the folder and runs the page's buttons.
`--no-serve` only renders, `--no-open` skips opening the browser, and
`ARBOR_REPORT_ROOT` overrides the root. **Every time a new version is served,
the page is opened** at `reportUrl` (default `http://localhost:8766/<ID>/`) and
shown to the user before anything else happens; if you rendered with
`--no-open` or `--no-serve`, open it yourself.

Never commit `report.json` (it lives in the work dir, outside the repos).

## Page behavior

- **Commit & push** commits each repo with `commitMessage` and pushes the work
  branch (never forced) after checking the branch
  matches the report (and `.workspace.json` when there is one), refusing
  `development`/`main`/`master`/`release-*`, refusing sensitive-looking files,
  and stripping AI trailers. On success it marks the repo pushed and
  re-renders. After a cycle that already committed and pushed, it stays
  disabled.
- **Uncommitted work is visible:** an amber **Uncommitted** line per repo, an
  `uncommitted` badge per file, and Commit & push stays enabled while anything
  is uncommitted.
- **Rerun** (and a banner when the working tree differs from what the page was
  generated from) starts a headless `claude -p` job in the work dir, denied
  every VCS write and `rm -rf`, that re-runs every test row with a `command`,
  marks rows it cannot re-run `"stale": "<why>"`, fixes `explanations` for
  changed hunks, regenerates `manualTests`, and records `hiccups`/`followups`.
  The previous `report.json` is backed up and restored if the result is invalid.
- **History** (key `h`) lists every run (Commit & push, Rerun, test-management publishing) newest
  first with its full log, kept in `~/.arbor-reports/<ID>/jobs.json`.
