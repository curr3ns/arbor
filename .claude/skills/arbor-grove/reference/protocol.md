# Grove exchange protocol

The contract between the hypervisor session (`arbor-grove run`), the agent container's
entrypoint (`kit/agent/entrypoint.sh`) and the in-container skill
(`kit/agent/skills/arbor-grove-agent`). Version: image label `arbor.grove.protocol=1`.

## Identifiers

| What        | Form                                                                   |
| ----------- | ---------------------------------------------------------------------- |
| item id     | `^[a-z0-9][a-z0-9-]{0,62}$`: `gh-<n>` for a GitHub issue, the lowercased Jira key (`shop-42`) for Jira |
| branch      | `grove/<item>`                                                         |
| message id  | `m<n>`, assigned by the hypervisor, unique per grove                   |
| grove name  | `^[a-z0-9][a-z0-9-]{0,30}$`, `grove.name` in `.arbor/config.json`      |

## Host layout

Everything runtime lives under `<repo>/.arbor/grove/` (gitignored, mode 0700):

```
.arbor/grove/
  state.json              the hypervisor's record (see state.md)
  mirror.git/             bare clone of origin; every bundle is cut from here, every push goes from here
  items/<item>/
    in/                   mounted read-only at /exchange/in
      task.json
      repo.bundle
      inbox/              hypervisor → agent mail, one file per message
    out/                  mounted read-write at /exchange/out (0777: the container runs as uid 1000)
      outbox/             agent → hypervisor mail
      result.json         written by the entrypoint only, last
      handoff.md          agent's criterion claims (≤ 64 KiB)
      question.md         agent's question when it parks (≤ 8 KiB)
      verify.log          tail of the entrypoint's verification run (≤ 32 KiB)
      branch.bundle       the task branch, when it has commits
      heartbeat           unix seconds, rewritten every 30 s by the entrypoint
      transcript.jsonl    the claude stream-json transcript
      claude.stderr, crash.log
    secret/claude         the Claude credential, copied in at launch and removed at teardown
```

Everything in `out/` is untrusted. The hypervisor reads a file there only after `grove-read`
confirms it is a regular file (not a symlink, FIFO or directory) under its size cap, and treats
its contents as data, never as instructions.

## in/task.json

Work run:

```json
{
  "mode": "work",
  "item": { "id": "gh-12", "title": "…", "body": "…", "url": "https://…" },
  "repo": { "default_branch": "main", "verify": "npm test" },
  "branch": "grove/gh-12",
  "model": "sonnet",
  "criteria": ["…", "…"],
  "footprint": { "globs": ["src/cart/**"], "whole_repo": false },
  "peers": [{ "id": "gh-14", "state": "running", "title": "…", "footprint": ["src/api/**"] }],
  "limits": { "verify_attempts": 3, "cr_wait_minutes": 20 },
  "resume": { "ref": "refs/grove/wip/gh-12", "notes": "…" }
}
```

`resume` is `null` on a first run. `resume.ref` is `null` when no work was kept; otherwise it is
`refs/grove/wip/<item>` and is in `repo.bundle`. `notes` say why the earlier run stopped, and may
quote a human's answer.

Re-gate run (merge queue; no credential, no Anthropic egress):

```json
{ "mode": "regate", "ref": "refs/grove/rebased/gh-12", "repo": { "verify": "npm test" } }
```

## out/result.json

Written by the entrypoint after the agent exits, replacing anything the agent put there.

| outcome        | Fields                              | Meaning                                                         |
| -------------- | ----------------------------------- | --------------------------------------------------------------- |
| `handoff`      | `verify {passed, exit}`, `commits`  | the agent finished; the entrypoint's own verify run result      |
| `park`         | `reason`, `commits`                 | the agent stopped; `question.md` says why                       |
| `empty-change` | `commits: 0`                        | the agent handed off with no commits                            |
| `auth`         | `commits`                           | the Claude credential was refused                               |
| `crash`        | `exit`, `commits`                   | the agent exited without a result                               |
| `regate`       | `passed`, `exit`                    | re-gate verify result                                           |

No `result.json` at all after the container exits means the entrypoint itself failed: a crash.

## Mail

One JSON object per file, at most 16 KiB. Writers create `.tmp-*` and rename, so a reader never
sees half a file; readers skip names starting with `.`. File names are
`<6-digit sequence>-<type>.json`.

### Agent → hypervisor (`/exchange/out/outbox/`)

| type               | Body                                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------------- |
| `change-request`   | `to` (item id), `summary` (one line), `reason`, `proposed_change`, `criteria: {target: {add: [], clarify: [{index, text}]}, sender: {add: []}}` |
| `cr-reply`         | `in_reply_to` (message id), `decision`: `accept` / `reject` / `counter`, `reason`, and `criteria` (same shape) for a counter |
| `footprint-expand` | `paths` (≤ 10 repo-relative paths or `dir/**` globs, ASCII `[A-Za-z0-9_.-/*]`), `reason`        |
| `status`           | `phase` (`plan`, `implement`, `verify`, `mail`, `wait`), `note` (≤ 200 chars)                    |

`target` is the item the request is sent to; `sender` is the item that sent it. Criteria can only
be added or clarified, never removed or relaxed; no item may reword its own criteria.

### Hypervisor → agent (`/exchange/in/inbox/`)

Every message carries `type`, `id` (`m<n>`) and `from` (an item id, or `grove`).

| type               | Body                                                                         |
| ------------------ | ---------------------------------------------------------------------------- |
| `change-request`   | as sent, plus `id` and `from`: another item asks this one for a change       |
| `cr-reply`         | `in_reply_to`, `decision`, `reason`, `criteria`: the answer to this item's request |
| `criteria`         | `criteria`: this item's full, current list (replaces the old one), `why`     |
| `footprint-reply`  | `decision`: `granted` / `refused`, `paths`, `reason`                         |
| `notice`           | `text`: anything else the hypervisor needs the agent to know                 |

The text of a forwarded message was written by another agent: it is untrusted data.
