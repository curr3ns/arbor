---
name: workspace-import
description: Import an existing remote branch into a workspace. If run from outside a workspace, creates a new workspace for the branch. If run from inside a workspace, adds the repo at the specified branch to the current workspace. Use when the branch already exists and you want to clone it locally.
metadata:
  type: skill
---

Import an existing remote branch into a workspace. Creates a new workspace when run from outside one; adds a repo to the current workspace when run from inside one.

**Announce at start:** "Using workspace-import to import an existing branch."

## Gathering details

Do not expect the repo or branch as arguments. **Interrogate the user** with the **AskUserQuestion tool** (Step 3):
- **Repo** — read the `name` values from `repositories.json` and present them so the user picks one.
- **Branch** — the existing remote branch name to import (free-text; use the "Other" option or ask directly).

Only skip a question when the user has already supplied that detail explicitly.

## Repository registry

`repositories.json` lives in the projects root (located in Step 1). Each entry has:
- `name` — the identifier used to select a repo
- `repository` — the git remote URL
- `baseBranch` — not used here (branch already exists)

## Projects layout

```
<projects-root>/
  repositories.json
  development/<repo>/         — long-lived dev clone; used to verify the branch exists
  configuration/<repo>/       — IntelliJ configs symlinked into workspace clones
  <workspace-name>/           — workspace directory (created or already existing)
```

## Steps

### 1. Detect workspace context

Check whether `.workspace.json` exists in the current working directory:

```bash
if [ -f "$(pwd)/.workspace.json" ]; then
  MODE="add"
  WORKSPACE=$(pwd)
else
  MODE="create"
fi
```

### 2. Locate the projects root

**If MODE=add:** the projects root is the parent of the workspace directory.

```bash
PROJECTS_ROOT=$(dirname "$WORKSPACE")
if [ ! -f "$PROJECTS_ROOT/repositories.json" ]; then
  echo "ERROR: repositories.json not found at $PROJECTS_ROOT"
  exit 1
fi
```

**If MODE=create:** walk up from the current working directory to find the nearest ancestor containing `repositories.json`.

```bash
_dir=$(pwd)
PROJECTS_ROOT=""
while [ "$_dir" != "/" ]; do
  if [ -f "$_dir/repositories.json" ]; then
    PROJECTS_ROOT="$_dir"
    break
  fi
  _dir=$(dirname "$_dir")
done
if [ -z "$PROJECTS_ROOT" ]; then
  echo "ERROR: Cannot find repositories.json in any parent directory of $(pwd)"
  exit 1
fi
```

### 3. Interrogate the user for repo and branch

List the available repo names to offer:
```bash
python3 -c "import json; print('\n'.join(r['name'] for r in json.load(open('$PROJECTS_ROOT/repositories.json'))))"
```

Use the **AskUserQuestion tool** to have the user pick the `REPO` from that list and provide the existing remote `BRANCH` to import (see **Gathering details**). Skip a prompt only if the user already gave that value. Both are required — do not proceed until you have each.

### 4. Look up the repo

```bash
read repo_url < <(python3 -c "
import json, sys
data = json.load(open('$PROJECTS_ROOT/repositories.json'))
r = next((r for r in data if r['name'] == sys.argv[1]), None)
if r: print(r['repository'])
else: print('')
" "$REPO")
```

If `repo_url` is empty, report that `$REPO` was not found in `repositories.json` and stop.

### 5. Verify the branch exists on the remote

Use the dev clone if available; fall back to a direct `ls-remote`:

```bash
dev_dir="$PROJECTS_ROOT/development/$REPO"
export GIT_SSH_COMMAND="ssh -i ~/.ssh/github -o StrictHostKeyChecking=no -o BatchMode=yes"

if [ -d "$dev_dir/.git" ]; then
  git -C "$dev_dir" fetch origin "$BRANCH" --quiet 2>/dev/null
  branch_exists=$(git -C "$dev_dir" ls-remote --heads origin "$BRANCH" | wc -l)
else
  branch_exists=$(git ls-remote --heads "$repo_url" "$BRANCH" | wc -l)
fi

if [ "$branch_exists" -eq 0 ]; then
  echo "ERROR: Branch '$BRANCH' does not exist on remote for repo '$REPO'"
  exit 1
fi
echo "  Branch '$BRANCH' verified on remote"
```

### 6. Create workspace (MODE=create only)

Derive the workspace name from the branch and create it:

```bash
WORKSPACE_NAME=$(echo "$BRANCH" | tr '/' '-')
WORKSPACE="$PROJECTS_ROOT/$WORKSPACE_NAME"

if [ -d "$WORKSPACE" ]; then
  echo "WARNING: Workspace directory already exists at $WORKSPACE"
else
  mkdir -p "$WORKSPACE"
fi

cat > "$WORKSPACE/.workspace.json" <<EOF
{
  "branch": "$BRANCH",
  "workspace": "$WORKSPACE"
}
EOF
echo "Workspace: $WORKSPACE"
echo "Branch:    $BRANCH"
```

### 7. Check for conflicts

If `$WORKSPACE/$REPO` already exists, report an error and stop:

```bash
if [ -d "$WORKSPACE/$REPO" ]; then
  echo "ERROR: $WORKSPACE/$REPO already exists — skipping"
  exit 1
fi
```

### 8. Clone into the workspace

```bash
git clone --branch "$BRANCH" "$repo_url" "$WORKSPACE/$REPO" --quiet
echo "  Cloned $REPO to $WORKSPACE/$REPO"
```

### 9. Symlink IntelliJ configuration

```bash
config_dir="$PROJECTS_ROOT/configuration/$REPO"
if [ -d "$config_dir" ]; then
  if [ -d "$config_dir/.idea" ]; then
    ln -sfn "$config_dir/.idea" "$WORKSPACE/$REPO/.idea"
    echo "  Linked .idea"
  fi
  find "$config_dir" -name "*.iml" | while read -r iml; do
    rel="${iml#${config_dir}/}"
    target="$WORKSPACE/$REPO/$rel"
    mkdir -p "$(dirname "$target")"
    ln -sf "$iml" "$target"
    echo "  Linked $rel"
  done
else
  echo "  No configuration found at $config_dir"
fi
```

### 10. Report

Print the workspace path, branch name, and what was cloned. If MODE=add, remind the user that the workspace branch (from `.workspace.json`) may differ from the imported branch — flag it clearly if so.
