# Parking

When the grove cannot go on with an item it parks it: records `park: {reason, question, at}`
(`$KIT/grove-state`), comments on the issue (`$KIT/grove-gh comment <n>`, body as a heredoc), and
swaps the labels (`$KIT/grove-gh label <n> -agent:working +agent:needs-clarification` on GitHub;
`agent-working` → `agent-needs-clarification` on Jira). The comment quotes the question as
a blockquote (so an `@grove` an agent wrote into it can never count as an answer) and ends with:

> Answer with a comment that starts with `@grove`, or run `/arbor-grove answer <item> "<text>"`.

## Answers

An answer counts when it is either:

- `/arbor-grove answer <item> "<text>"` (writes `.arbor/grove/answers/<item>.md`), or
- an issue comment posted **after** the park comment whose first non-quoted line starts with
  `@grove`, from a trusted human: on GitHub an author with `admin`, `maintain` or `write`
  permission and not a bot (`$KIT/grove-gh trusted <login>` prints `true`); on Jira an account in `grove.jira.trusted_accounts`. Quoted lines (`>`) and
  fenced code are ignored when finding the `@grove` line.

On an answer: append it to the item's `notes` (fenced as a human answer), acknowledge it on the
issue, swap the labels back, and move the item to `queued` (re-triage) for the reasons marked
**T** below, else to `ready` (resume from its WIP when it has one). Closing the issue of a parked
item moves it to `failed`.

`host-verify-guard` is the exception: an answer whose first word is `approve` means a human read
the guarded files' changes and accepts handing them to the host's Docker daemon. Run
`$KIT/grove-host-verify approve <item>` (it records exactly the content approved), then set the
item `reviewing` and run the review again from the intent gate (Exits, **Review** step 2) on
`refs/grove/wip/<item>`. Any other answer is guidance: `ready`, as above, and the agent reworks
the change to need no guarded edit, or a smaller one. A later change to an approved file parks
again.

## Reasons

| Reason                 | Raised when                                                                | Resolve by                                    |
| ---------------------- | -------------------------------------------------------------------------- | --------------------------------------------- |
| `needs-criteria` **T** | triage found the item too vague; the question is triage's                   | answering the question                        |
| `question`             | the agent hit an ambiguity with no defensible default                       | answering the question                        |
| `criteria-needs-human` **T** | criteria contradict each other or the item, or would need relaxing     | editing the issue, then answering             |
| `judge-failed`         | triage or the intent gate gave no valid verdict twice                       | answering (often: "retry")                    |
| `gate-failed`          | verification still failed after the agent's last attempt                    | answering with guidance                       |
| `rework-limit`         | the intent gate or re-gate failed `limits.rework` times                     | answering with guidance                       |
| `crash-limit`          | the container crashed `limits.crash` times                                  | fixing the cause (image, verify), answering   |
| `timeout`              | the run passed `limits.run_minutes`, or the heartbeat went stale and stayed | answering (maybe splitting the issue)         |
| `empty-change`         | the agent handed off with no commits, or the rebase left nothing to merge   | answering, or closing as already done         |
| `protected-path`       | the change touches `.arbor/`, `.grove/`, `.github/` or `.gitlab-ci*`         | making that change by hand in a PR            |
| `unreviewable-change`  | binary, symlink, submodule or LFS changes, or a merge commit                | answering with how to avoid them              |
| `diff-too-large`       | more than `limits.max_diff_lines` changed lines                             | splitting the issue                           |
| `footprint-violation`  | files changed outside the footprint plus grants                            | answering (widen, or tell it to stay inside)  |
| `host-verify-guard`    | the change touches a `host_verify.guard` file (what the host's Docker daemon runs) | reviewing those files' diff, then answering `approve`, or with guidance |
| `footprint-denied`     | the agent needed paths the grove refused                                    | answering once the other item is done         |
| `cr-timeout`           | a change request the agent depended on got no answer in time               | answering                                     |
| `credential-in-diff`   | added lines look like a credential, or hold the grove's own                 | **rotate the credential first**, then review the WIP by hand |
| `merge-error`          | the default branch kept moving during the merge (3 tries)                   | answering ("retry")                           |
| `push-refused`         | the push was rejected (protected branch, hooks)                             | fixing branch rules or using `pr_mode`        |
| `pr-closed`            | `pr_mode`: the PR was closed without merging                                | answering, or closing the issue               |
| `killed`               | `/arbor-grove stop` ended the run                                           | answering ("resume")                          |

A `credential-in-diff` item's WIP never leaves the mirror: nothing is pushed, no PR is opened, and
the park comment names only the files, never the matched text.
