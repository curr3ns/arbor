# GitHub templates for issue mode

`arbor-auto-work` in issue mode (`issue:<n>` or `issue:next`) treats a GitHub
issue as the cycle's contract: it claims the issue with a label, restates its
acceptance criteria as an intent contract, verifies the diff against those
criteria at the intent gate, and closes the issue on merge. That only works if
issues actually carry checkable criteria and the labels exist — which is what
these templates and commands set up.

Adopting is a one-off per repo; the work cycle itself needs no configuration.

## Install

Copy the templates into the repo, keeping the layout:

```bash
cp -R ~/.claude/skills/arbor-auto-work/templates/github/. .github/
```

That gives you `.github/ISSUE_TEMPLATE/{feature,bug,config}.yml` and
`.github/pull_request_template.md`. Adjust the placeholders — the example
packages in `feature.yml`, and the gate command named in the pull request
template's gate-evidence comment — to match the project.

## Create the labels

The label set is the cycle's lock and its status record, so create it before the
first issue-mode run:

```bash
gh label create "agent:working"             -c "#0e8a16" -d "A cycle owns this issue right now"
gh label create "agent:done"                -c "#5319e7" -d "Shipped and merged by a cycle"
gh label create "agent:blocked"             -c "#b60205" -d "Implemented, but the gate will not pass"
gh label create "agent:needs-clarification" -c "#fbca04" -d "Ambiguous intent; questions are in the comments"
gh label create "p0" -c "#b60205" -d "Highest selection priority"
gh label create "p1" -c "#d93f0b" -d "Normal selection priority"
gh label create "p2" -c "#fef2c0" -d "Lowest selection priority"
```

`issue:next` orders on `p0` > `p1` > `p2` > unlabelled, so priority labels are
optional — an unlabelled issue is still selectable, just last.

## Why the criteria field is required

The intent gate dispatches a fresh subagent that has not seen the
implementation, hands it the issue plus the branch diff, and asks for a verdict
per criterion — `satisfied` with the file and line, or `not satisfied`. It
defaults to `not satisfied` when it cannot find the evidence. An issue whose
criteria read "works well" therefore fails its own gate: there is nothing to
point at. One checkable statement per line — an input and an output, a visible
behaviour, an error case — is what makes the merge decision mechanical.
