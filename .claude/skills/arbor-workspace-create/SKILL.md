---
name: arbor-workspace-create
description: Set up a new feature workspace by creating a remote branch for each repo and cloning it into a named workspace directory with symlinked IntelliJ configs. Use when starting new feature work that spans one or more repositories.
metadata:
  type: skill
---

Set up a new feature workspace: create a remote branch for each repository, clone it into a named workspace directory, and symlink IntelliJ configurations.

**Announce at start:** "Using arbor-workspace-create to set up a new workspace."

## Gathering details

Do not expect the branch name, description, or repo list as arguments. **Interrogate the user** for each detail you don't already have, using the **AskUserQuestion tool**. Only skip a question when the user has already supplied that detail explicitly in the conversation; use what they gave and ask for the rest.

Collect:
- **Branch type** — `feature`, `bugfix`, or `hotfix`. Present these as options.
- **Ticket / identifier** — e.g. `DEV-1234`. Free-text (use the "Other" option or ask directly).
- **Description** — a short phrase describing the work; slugified and appended to the branch name and workspace directory name.
- **Repos** — which repositories to include. Read the `name` values from `repositories.json` (after locating the projects root in Step 1) and present them as a multi-select list.

Ask for these before proceeding. The branch name is assembled from the branch type and ticket (e.g. `feature/DEV-1234`), so no prefix validation is needed — you only offer the three valid types.

## Repository registry

`repositories.json` lives in the projects root (located in Step 1). It is a JSON array where each entry has:
- `name` — the identifier used to select a repo
- `repository` — the git remote URL
- `baseBranch` — the branch to create the new feature branch from

## Projects layout

The projects root contains:
- `repositories.json` — repo registry (used to locate the root)
- `development/<repo>/` — long-lived dev clone; used to push the new branch to the remote without a local checkout
- `configuration/<repo>/` — stores IntelliJ `.idea/` and `.iml` files symlinked into workspace clones
- `<workspace-name>/` — the workspace directory created by this command

A `.workspace.json` is written at the workspace root so `arbor-workspace-add` and `arbor-workspace-import` can find the branch name later.

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

### 2. Interrogate the user for details

Read the available repo names so you can offer them:
```bash
python3 -c "import json; print('\n'.join(r['name'] for r in json.load(open('$PROJECTS_ROOT/repositories.json'))))"
```

Then use the **AskUserQuestion tool** to collect the details listed in **Gathering details** above — branch type, ticket/identifier, description, and which repos (multi-select from the names above). Ask only for what the user hasn't already provided.

Assemble the branch name and derived paths from their answers:
```bash
BRANCH_PREFIX="${BRANCH_TYPE}/${TICKET}"   # e.g. feature/DEV-1234
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
