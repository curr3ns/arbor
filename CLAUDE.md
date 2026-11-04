# arbor

Personal Claude Code skills (workspace setup and commit-message generation), symlinked into
`~/.claude/skills` by `install.sh`. This repo is public: keep the skills generic, with no
employer-specific names, hosts or accounts.

## Workflow

- **Tickets:** none. This repo is tooling and doesn't use tickets, so branches are `<type>/<slug>`
  and commit subjects carry no ID.
- **Gate:** none beyond reading the changed skill end to end; after adding or removing a skill,
  run `./install.sh` and check `~/.claude/skills`.
