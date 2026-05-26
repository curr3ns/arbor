---
name: workspace-start
description: Set up a new feature workspace by creating a remote branch for each repo and cloning it into a named workspace directory with symlinked IntelliJ configs.
---

# workspace-start

Set up a new feature workspace: create a remote branch for each repository, clone it into a named workspace directory, and symlink IntelliJ configurations.

**Announce at start:** "Using workspace-start to set up a new workspace."

## Input

`/workspace-start <branch_name> "<description>" <repo1> [repo2 ...]`

- `branch_name` — must start with `feature/`, `bugfix/`, or `hotfix/` followed by a ticket or identifier (e.g. `feature/DEV-1234`). Reject with an error if the prefix is not one of those three — do not proceed.
- `description` — quoted string describing the work; slugified and appended to the branch name and workspace directory name
- `repos` — one or more repo names matching entries in `repositories.json`

## Repository registry

`repositories.json` lives in the projects root (located in Step 1). It is a JSON array where each entry has:
- `name` — the identifier used as the `<repo>` argument
- `repository` — the git remote URL
- `baseBranch` — the branch to create the new feature branch from

## Projects layout

The projects root contains:
- `repositories.json` — repo registry (used to locate the root)
- `development/<repo>/` — long-lived dev clone; used to push the new branch to the remote without a local checkout
- `configuration/<repo>/` — stores IntelliJ `.idea/` and `.iml` files symlinked into workspace clones
- `<workspace-name>/` — the workspace directory created by this skill

A `.workspace.json` is written at the workspace root so `/workspace-add` can find the branch name later.

## Steps

### 1. Locate the projects root

Walk up from the current working directory to find the nearest ancestor that contains `repositories.json`. Stop and report an error if none is found.

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
echo "Projects root: $PROJECTS_ROOT"
```

### 2. Parse and validate arguments

Parse `$ARGUMENTS`:
- First token → `BRANCH_PREFIX`
- Quoted string → `DESCRIPTION` (strip quotes)
- Remaining tokens → repo list

Reject with a clear error if `BRANCH_PREFIX` does not start with `feature/`, `bugfix/`, or `hotfix/`.

Compute derived names:
```bash
DESC_SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
BRANCH_NAME="${BRANCH_PREFIX}-${DESC_SLUG}"
WORKSPACE_NAME=$(echo "$BRANCH_NAME" | tr '/' '-')
WORKSPACE="$PROJECTS_ROOT/$WORKSPACE_NAME"
```

### 3. Create workspace directory and metadata

```bash
mkdir -p "$WORKSPACE"
cat > "$WORKSPACE/.workspace.json" <<EOF
{
  "branch": "$BRANCH_NAME",
  "workspace": "$WORKSPACE"
}
EOF
echo "Workspace: $WORKSPACE"
echo "Branch:    $BRANCH_NAME"
```

### 4. For each repo

Repeat the following for every repo in the list.

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

### 5. Report

Print the workspace path, branch name, and a summary of what was cloned. Flag any repos that failed or were skipped.
