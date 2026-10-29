# Project profiles

A project profile carries everything about a codebase that is too specific, or
too private, to live in this skill: which repos exist and what they do, how to
run the stack locally, how to build test data, which environments exist, and
any house rules. It stays outside this skill's repository.

## Where it lives

Step 0 walks up from the current directory and uses the **nearest**
`.arbor/auto-work.md`. For a multi-repo projects root (the directory holding
`repositories.json`), that is `<projects root>/.arbor/auto-work.md`, so it
applies to every workspace under it. A single repo may carry its own. No
profile is a normal state: the cycle runs on this skill alone.
`arbor-auto-setup` builds or refreshes a profile and its provider mappings by
interviewing the user.

Record the profile's path in the report's `profile` field, so a Rerun reads it
too.

## How it applies

The profile is read in full at step 0 and handed to every phase that needs it
(plan, implement, verify, review). It **adds to and narrows** this skill: its
hard rules are hard rules of the cycle, and where it names a command, a repo, a
service or a convention, that wins over a generic default. It never loosens a
gate: it cannot skip a suite, accept a partial run, or waive the intent gate.

## What it usually contains

Any of these sections; all optional.

- **Providers** — the ticket system (and its project key), the code host,
  and the VCS, each named or given a full mapping: the tools, the exact call
  per operation, and provider details such as label spellings, the selection
  query, and any closing keyword (`## Providers` in `SKILL.md`). A mapping
  shared by several projects goes in
  `~/.claude/arbor/providers/<vcs|host|tickets>/<name>.md` instead, and the
  profile just names the provider.
- **Test management** — the system that keeps the project's test cases, by
  the name of its mapping in `~/.claude/arbor/providers/tests/`
  (`references/report.md`).
- **Work-ID prefix** — the uppercase prefix for work IDs a ticket does not
  supply.
- **Hard rules** — house rules on top of this skill's (e.g. attribution policy
  for commits and change requests, branches never to touch).
- **Repo map** — repo name, role and stack, which repos are the usual set, and
  how to choose: following a call chain from UI to gateway to the owning API,
  where database changes go and how migrations are generated.
- **Lifecycle per repo** — e.g. which repos use the OpenSpec propose / apply /
  archive lifecycle.
- **Test commands per repo** — the fast-stage and slow-stage commands and the
  automation-suite commands, with any flags a local run needs.
- **Local stack** — how to bring services up (proxy setup, run configurations,
  ports, env), which environment the local stack points at.
- **Test data** — how to create users and records, which admin tools change
  their state, credentials location (never the credentials themselves), and
  how to confirm local services can see the data.
- **Report** — `reportUrl` (e.g. a local proxy host for the report server),
  `manualTestsForbid` (environment names and hosts the manual-test lint must
  flag), and a house-style manual-tests example to use instead of
  `references/manual-tests-example.md`.
- **Integration** — where finished work goes when it is not the default
  (e.g. always open a change request against the base branch, never merge).
- **Lessons** — where durable lessons about the environment are recorded.
