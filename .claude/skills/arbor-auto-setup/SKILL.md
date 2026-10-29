---
name: arbor-auto-setup
description: Use when setting up or refreshing the project profile and provider mappings that arbor-auto-work reads — a new machine, a new projects root or repo, a new ticket system, code host, VCS or test-management system, or when arbor-auto-work reports a missing or incomplete mapping. Interviews the user to build .arbor/auto-work.md and ~/.claude/arbor/providers/.
metadata:
  author: arbor
  version: "1.0"
---

# Arbor auto setup

Build the files `arbor-auto-work` reads before a cycle, by detecting what the
machine and repos already reveal and interviewing the user for the rest:

- the **project profile** — `.arbor/auto-work.md`, whose sections are defined
  in `~/.claude/skills/arbor-auto-work/references/profile.md` (read it first);
- the **provider mappings** — `~/.claude/arbor/providers/<vcs|host|tickets|tests>/<name>.md`
  (plus `<name>.json` for a VCS, per the docstring of
  `~/.claude/skills/arbor-auto-work/report/vcs.py`, and the JSON for test
  management described in `references/report.md`'s `## Test management`), with
  the operations listed in arbor-auto-work's `## Providers`.

Nothing else is written: no lessons files, no repo files, no config of other
tools. Never name a provider in this skill's own output conventions — every
provider detail comes from detection or the user.

## Steps

Create a todo per step.

1. **Locate.** Find the target: the nearest projects root (an ancestor holding
   `repositories.json`) → `<root>/.arbor/auto-work.md`; otherwise the current
   repository → `<repo>/.arbor/auto-work.md`. If a profile exists, read it: this
   run updates it in place, asking only about missing or changed sections.
   **If the target is inside a version-controlled repository**, check whether
   the file would be tracked and whether the remote is public; a profile holds
   private details, so offer to ignore the file or to place it at the projects
   root instead, and follow the answer.

2. **Detect before asking.** Gather everything the machine can tell you, and
   hold it as proposed answers:
   - each repo (from `repositories.json`, or the current one): its VCS, remote
     host, base branch, stack and build files, `CLAUDE.md`/`AGENTS.md`, CI spec,
     an `openspec/` directory, an automation-suite directory;
   - per repo, three distinct test commands — **fast stage** (the normal full
     build CI runs), **slow stage** (the build's own task that also runs specs
     the fast build skips; none if there is none), and **automation suite**
     (the whole end-to-end/API suite) — never one command filed under two;
   - existing mappings under `~/.claude/arbor/providers/`;
   - this session's tools: MCP servers (by tool-name prefix) and CLIs on PATH
     that match the remote host or a ticket link, and skills that look like a
     test-management system's.
   `.arbor/config.json`'s `roadmap.destination` names the ticket system when
   present.

3. **Interview.** Use AskUserQuestion, at most 4 questions per call, in this
   order of batches: providers; work-ID prefix, hard rules and integration
   route; local stack and test data; report settings and lessons location.
   Every question that has a detected answer offers it as the first option,
   marked "(Recommended)", with the evidence in its description; every
   question offers concrete options, never only free text. Skip any question
   the detection answered with certainty (a single remote host, a single
   ticket system in config) — state those findings in the next batch's text
   instead. Ask for credential **locations** only, never values.

4. **Build each missing mapping from the tools, not from the user.** For every
   operation the provider kind needs, find the call in the detected MCP tools
   or the CLI's `--help`, then prove it with read-only calls (access check, a
   status, a ticket read, a list). Details the tools expose — label spellings,
   workflow transitions, priority fields, change-request flags, template
   locations — come from those calls. Ask the user only for what the tools
   cannot show, as concrete options. An operation that stays unresolved is
   written into the mapping as `UNRESOLVED: <what is missing>`, never guessed.

5. **Review, then write.** Show the user the full draft of the profile and of
   every new or changed mapping in one message, and ask for approval or
   changes (AskUserQuestion: write / change something). Write only after
   approval: the profile at the target, mappings under
   `~/.claude/arbor/providers/`. Keep any existing content the user did not
   change.

6. **Verify and report gaps.** Run every VCS JSON command that is read-only
   (`current_branch`, `default_branch`, `untracked`, `uncommitted`) in one repo,
   compile any test-management `keyPattern`, and re-run each mapping's access
   check. Finish with a short summary: files written, what was detected versus
   answered, and a **gap list** — each `UNRESOLVED` entry or failed check with
   the arbor-auto-work step it will block (e.g. "Select unresolved → `ticket:next`
   fails at step 0").

## Profile shape

Sections in this order, each present only when it has content; headings match
`references/profile.md`:

```markdown
# Project profile — <projects root or repo name>

## Providers
Ticket system: <name>, project `<KEY>`. Code host: <name>. VCS: <name>.
Test management: <name or none>. Mappings: `~/.claude/arbor/providers/`.

## Work-ID prefix
## Hard rules
## Integration
## Repo map            (table: repo · role · stack · base branch; how to choose repos)
## Lifecycle per repo
## Tests per repo      (per repo: fast stage · slow stage · automation suite · local-run flags)
## Local stack
## Test data           (how to create data, admin tools, credential locations, environments)
## Report              (reportUrl, manualTestsForbid, manual-tests example path)
## Lessons
```

## Common mistakes

| Mistake | Instead |
| --- | --- |
| Asking the user for tool names, labels, flags or transitions | Read them from the session's tools and prove them read-only |
| Open questions, or more than 4 per call | Concrete options, detected answer first as "(Recommended)" |
| One command filed as both slow stage and automation suite | Three separate slots per repo; "none" is a valid answer |
| Mapping fields left blank or guessed | `UNRESOLVED: <what>` plus a gap-list entry |
| Writing before the user saw the draft | One review message, then write |
| Creating lessons files, repo files or config of other tools | Write only the profile and the mappings |
| Storing a password or token | Store where it lives (a vault, an env var name), never the value |
