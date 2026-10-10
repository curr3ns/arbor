# Grove configuration and state

## Configuration — `.arbor/config.json`, key `grove`

Written by `/arbor-grove init`; other top-level keys belong to other arbor skills (`roadmap` is
`arbor-auto-roadmap`'s) — read and rewrite only `grove`.

```json
{
  "grove": {
    "name": "shop",
    "default_branch": "main",
    "verify": "npm ci && npm test",
    "source": "github",
    "intake": { "label": null },
    "max_agents": 3,
    "models": { "agent": "sonnet", "triage": "sonnet", "gate": "opus", "judge": "sonnet" },
    "registries": ["registry.npmjs.org"],
    "credential_env": "CLAUDE_CODE_OAUTH_TOKEN",
    "pr_mode": false,
    "auto_merge_acknowledged": true,
    "jira": { "trusted_accounts": [] },
    "resources": { "cpus": 2, "memory_mb": 4096 },
    "limits": {
      "verify_attempts": 3, "rework": 2, "crash": 2, "run_minutes": 90,
      "cr_wait_minutes": 20, "max_diff_lines": 3000, "footprint_grants": 10
    }
  }
}
```

| Key                       | Meaning                                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| `name`                    | the grove's name: container, volume and label prefix (`^[a-z0-9][a-z0-9-]{0,30}$`)          |
| `verify`                  | the verification command, run in containers only — never on the host                     |
| `source`                  | `github` or `jira`; Jira uses `roadmap.jira.project` and its transitions                  |
| `intake.label`            | when set, only issues carrying this label are taken                                       |
| `max_agents`              | most work containers at once (re-gates do not count)                                      |
| `models`                  | `agent` runs in containers; `triage`, `gate`, `judge` are host subagents                   |
| `registries`              | extra hosts agents and re-gates may reach (port 443 unless `host:port`)                   |
| `credential_env`          | how the credential is exported in the container: `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY` |
| `pr_mode`                 | `true`: open a PR per item and never merge; `false`: auto-merge after the gates            |
| `auto_merge_acknowledged` | must be `true` for `pr_mode: false` — the operator accepted that issue authors are trusted |
| `jira.trusted_accounts`   | Jira account ids whose issues are taken and whose `@grove` answers count                  |
| `.arbor/agent.Dockerfile` | (a file, not a key) a project image `FROM arbor-grove-agent:latest` with the repo's toolchain |

## State — `.arbor/grove/state.json`

The hypervisor session is its only writer. Write it after every change, through
`$KIT/grove-state '<jq filter>' [--arg …]`, which replaces it atomically (`grove-state start`
creates it). Everything else can be rebuilt from it plus `grove-ps`.

```json
{
  "version": 1,
  "paused": false,
  "pause_reason": null,
  "next_message": 1,
  "merging": null,
  "queue": ["gh-12"],
  "threads": {
    "m3": { "from": "gh-12", "to": "gh-14", "summary": "…", "status": "open", "criteria": {} }
  },
  "items": {
    "gh-12": {
      "source": "github", "key": "12", "url": "https://github.com/o/r/issues/12",
      "title": "…", "body": "…", "author": "alice",
      "state": "running",
      "criteria": ["…"],
      "criteria_log": [{ "at": "2026-10-09T12:00:00Z", "via": "m3", "op": "add", "text": "…" }],
      "size": "M", "after": [],
      "footprint": { "globs": ["src/cart/**"], "whole_repo": false },
      "grants": [],
      "run": "20261009120000-work", "launched_at": 1760011200,
      "counts": { "crash": 0, "rework": 0, "land": 0 },
      "wip": true, "notes": "",
      "reviewed": null, "rebased": null, "pr": null,
      "park": null,
      "handled": ["20261009120000-work:000001-status.json"]
    }
  }
}
```

### Item states

| State       | Meaning                                                             | Next                                    |
| ----------- | ------------------------------------------------------------------- | --------------------------------------- |
| `queued`    | taken in; needs triage                                              | `ready`, `parked`                       |
| `ready`     | has criteria and footprint; waits for a slot                        | `running`                               |
| `running`   | a work container is up (`run` names it)                             | `reviewing`, `ready` (rework), `parked` |
| `reviewing` | harvested; mechanical checks and intent gate in progress            | `merging`, `ready` (rework), `parked`   |
| `merging`   | in `queue`; when first, prepared, re-gated and pushed               | `done`, `in-review`, `ready`, `parked`  |
| `in-review` | `pr_mode`: a PR is open; a human merges                             | `done`, `parked`                        |
| `parked`    | waiting for a human (`park: {reason, question, at, comment}`)       | `queued`, `ready`, `failed`             |
| `done`      | merged and closed                                                   | —                                       |
| `failed`    | the issue was closed while parked                                   | —                                       |

`handled` lists the events already acted on (`<run>:<file>` for mail, `exit:<run>` for exits) so a
re-armed watcher's replay is ignored.
