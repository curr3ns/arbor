---
name: workspace-add
description: Add one or more repositories to an existing workspace. Use when the user wants to add repos to a workspace that was created by workspace-create. Must be run from inside the workspace directory.
metadata:
  type: skill
---

Add one or more repositories to an existing workspace created by `workspace-create`.

**Announce at start:** "Using workspace-add to add repos to the current workspace."

## Input

One or more repo names matching entries in `repositories.json`.

Must be run from a workspace directory that contains `.workspace.json` (created by `workspace-create`).

## Repository registry

`repositories.json` lives in the projects root (located via `.workspace.json`). Each entry has:
- `name` — the identifier used as the `<repo>` argument
- `repository` — the git remote URL
- `baseBranch` — used if the branch doesn't yet exist on the remote

## Steps

### 1. Read workspace metadata

Verify `.workspace.json` exists in the current working directory. If not, stop and report that this command must be run from a workspace directory created by `workspace-create`.

```bash
WORKSPACE=$(pwd)
WORKSPACE_JSON="$WORKSPACE/.workspace.json"

if [ ! -f "$WORKSPACE_JSON" ]; then
  echo "ERROR: .workspace.json not found in $WORKSPACE"
  echo "Run this command from a workspace directory created by workspace-create"
  exit 1
fi

BRANCH_NAME=$(python3 -c "import json; d=json.load(open('$WORKSPACE_JSON')); print(d['branch'])")
echo "Workspace: $WORKSPACE"
echo "Branch:    $BRANCH_NAME"
```

### 2. Locate the projects root

The projects root is the parent of the workspace directory (workspaces are created directly inside the projects root). Verify `repositories.json` is present there.

```bash
PROJECTS_ROOT=$(dirname "$WORKSPACE")
if [ ! -f "$PROJECTS_ROOT/repositories.json" ]; then
  echo "ERROR: repositories.json not found at $PROJECTS_ROOT"
  exit 1
fi
```

### 3. For each repo

Repeat the following for every repo in the list.

**Check for conflicts** — if the repo directory already exists in the workspace, print an error and skip it.

**Look up the repo** in `repositories.json`:
```bash
read repo_url base_branch < <(python3 -c "
import json, sys
data = json.load(open('$PROJECTS_ROOT/repositories.json'))
r = next((r for r in data if r['name'] == sys.argv[1]), None)
if r: print(r['repository'], r.get('baseBranch', ''))
else: print('', '')
" "$repo")
```
If `repo_url` is empty, print an error for this repo and continue to the next one.

**Create the branch on the remote** using the dev clone as a conduit (no checkout needed):
```bash
dev_dir="$PROJECTS_ROOT/development/$repo"
export GIT_SSH_COMMAND="ssh -i ~/.ssh/github -o StrictHostKeyChecking=no -o BatchMode=yes"

if [ -d "$dev_dir/.git" ]; then
  git -C "$dev_dir" fetch origin "$base_branch" --quiet 2>/dev/null
  if git -C "$dev_dir" ls-remote --exit-code --heads origin "$BRANCH_NAME" &>/dev/null; then
    echo "  Branch already exists on remote"
  else
    git -C "$dev_dir" push origin "refs/remotes/origin/${base_branch}:refs/heads/${BRANCH_NAME}" --quiet
    echo "  Created branch $BRANCH_NAME from $base_branch"
  fi
else
  echo "  WARNING: No development clone at $dev_dir — branch must be created manually"
fi
```

**Clone into the workspace:**
```bash
git clone --branch "$BRANCH_NAME" "$repo_url" "$WORKSPACE/$repo" --quiet
echo "  Cloned to $WORKSPACE/$repo"
```

**Symlink IntelliJ configuration:**
```bash
config_dir="$PROJECTS_ROOT/configuration/$repo"
if [ -d "$config_dir" ]; then
  if [ -d "$config_dir/.idea" ]; then
    ln -sfn "$config_dir/.idea" "$WORKSPACE/$repo/.idea"
    echo "  Linked .idea"
  fi
  find "$config_dir" -name "*.iml" | while read -r iml; do
    rel="${iml#${config_dir}/}"
    target="$WORKSPACE/$repo/$rel"
    mkdir -p "$(dirname "$target")"
    ln -sf "$iml" "$target"
    echo "  Linked $rel"
  done
else
  echo "  No configuration found at $config_dir"
fi
```

### 4. Report

Print a summary of cloned repos and the branch name. Flag any repos that failed, were skipped, or already existed.
