---
name: arbor-workspace-init
description: Initialize a new projects root directory structure, populate repositories.json interactively, and clone each repo into the development folder. Use once per machine before using arbor-workspace-create or arbor-workspace-add.
metadata:
  type: skill
---

Bootstrap a new projects root on any machine. Creates the expected directory layout, builds `repositories.json` from user input, and clones each repo into `development/`.

Run this once per machine before using `arbor-workspace-create` or `arbor-workspace-add`.

**Announce at start:** "Using arbor-workspace-init to set up a new projects root."

## Gathering details

Do not expect the projects-root path as an argument. **Interrogate the user** with the **AskUserQuestion tool**: ask whether to use the current working directory as the projects root or a different absolute path (offer the current directory as an option, and let them supply another via "Other"). The repository list is gathered interactively in Step 3. Skip a prompt only if the user already gave that detail explicitly.

## Projects root layout

After init, the projects root will contain:

```
<projects-root>/
  repositories.json       # repo registry consumed by all workspace commands
  development/            # long-lived clones, one per repo; used to push branches remotely
  configuration/          # optional IntelliJ configs (.idea/, .iml) per repo
```

`configuration/` is not created automatically — it is populated manually or by other tooling as needed.

## `repositories.json` schema

A JSON array. Each entry describes one managed repository:

```json
[
  {
    "name": "my-service",
    "repository": "git@github.com:org/my-service.git",
    "baseBranch": "development"
  }
]
```

- `name` — short identifier used to select a repo in all workspace commands; must be unique
- `repository` — git remote URL (SSH recommended)
- `baseBranch` — the branch new feature branches are forked from (e.g. `development`, `main`, `develop`)

Multiple entries may point to the same `repository` URL with different `name` and `baseBranch` values (e.g. to track multiple long-lived branches of a monorepo).

## Steps

### 1. Resolve the projects root

Ask the user for the projects root as described in **Gathering details** (default: the current working directory). Then:

```bash
PROJECTS_ROOT="<answer, defaulting to $(pwd)>"
echo "Projects root: $PROJECTS_ROOT"
```

If the path does not exist, create it:
```bash
mkdir -p "$PROJECTS_ROOT"
```

If `repositories.json` already exists there, warn the user and ask whether to overwrite or abort before continuing.

### 2. Create directory structure

```bash
mkdir -p "$PROJECTS_ROOT/development"
echo "Created: $PROJECTS_ROOT/development/"
```

### 3. Build repositories.json interactively

Prompt the user for their repository list. For each repo, collect:
- `name` — short identifier (no spaces)
- `repository` — git remote URL
- `baseBranch` — default branch to fork from

Use the **AskUserQuestion tool** to ask how they want to provide the list:
- **Enter repos one at a time** — prompt for each field, repeat until they say done
- **Paste JSON directly** — accept a JSON array and validate it against the schema above

Validate each entry:
- `name` must be non-empty and unique within the list
- `repository` must be non-empty
- `baseBranch` must be non-empty

Write the validated array to disk:
```bash
python3 -c "
import json
data = <collected_entries>
with open('$PROJECTS_ROOT/repositories.json', 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
echo "Wrote repositories.json with ${#entries[@]} entries"
```

### 4. Clone each repo into development/

For each entry in `repositories.json`, clone the `baseBranch` into `development/<name>/`:

```bash
export GIT_SSH_COMMAND="ssh -i ~/.ssh/github -o StrictHostKeyChecking=no -o BatchMode=yes"

for entry in <entries>; do
  name=<entry.name>
  repo_url=<entry.repository>
  base_branch=<entry.baseBranch>
  dev_dir="$PROJECTS_ROOT/development/$name"

  if [ -d "$dev_dir" ]; then
    echo "  $name: already exists at $dev_dir, skipping"
    continue
  fi

  echo "  Cloning $name ($base_branch)..."
  git clone --branch "$base_branch" "$repo_url" "$dev_dir" --quiet
  echo "  $name: cloned to $dev_dir"
done
```

If a clone fails (bad URL, missing branch, auth error), print the error and continue with the remaining repos. Report all failures at the end.

### 5. Report

Print a final summary:
- Projects root path
- Number of repos written to `repositories.json`
- Which repos were cloned successfully, which were skipped, which failed
- Next step hint: "Run `arbor-workspace-create` from any subdirectory of this projects root to create a feature workspace."
