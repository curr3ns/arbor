# Shared helpers for the grove host scripts. Sourced, never run.
# Every script runs from inside the target repo (or with GROVE_REPO set) and reads the `grove`
# block of <repo>/.arbor/config.json. Runtime files live in <repo>/.arbor/grove/.

set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() { echo "grove: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "$1 is required"; }
need jq
need git

ROOT="${GROVE_REPO:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
[ -n "$ROOT" ] || die "run from inside the target repository (or set GROVE_REPO)"
CONFIG="$ROOT/.arbor/config.json"
GD="$ROOT/.arbor/grove"
MIRROR="$GD/mirror.git"

# cfg <jq path under .grove> [default]
cfg() {
  local v=""
  [ -f "$CONFIG" ] && v=$(jq -r ".grove$1 // empty | if type == \"array\" then join(\",\") else tostring end" "$CONFIG")
  printf '%s' "${v:-${2:-}}"
}

NAME="$(cfg .name)"
[ -n "$NAME" ] || die "no grove.name in $CONFIG — run /arbor-grove init first"
[[ "$NAME" =~ ^[a-z0-9][a-z0-9-]{0,30}$ ]] || die "invalid grove.name: $NAME"
BASE="$(cfg .default_branch main)"
AGENT_IMAGE="${GROVE_AGENT_IMAGE:-$( [ -f "$ROOT/.arbor/agent.Dockerfile" ] && echo "arbor-grove-agent-$NAME:latest" || echo arbor-grove-agent:latest )}"
EGRESS_IMAGE="${GROVE_EGRESS_IMAGE:-arbor-grove-egress:latest}"
EGRESS_NET="arbor-grove-egress"
CREDENTIAL_FILE="${GROVE_CREDENTIAL_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/arbor-grove/credential}"

valid_item() { [[ "$1" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]] || die "invalid item id: $1"; }
item_dir() { printf '%s/items/%s' "$GD" "$1"; }
cname() { printf 'arbor-grove-%s-%s-%s' "$NAME" "$1" "$2"; } # cname <item> <agent|egress|ws|sock>

# Containers of this grove (optionally one item), by label: the only ones any script touches.
grove_containers() {
  local f=(--filter "label=arbor.grove=$NAME")
  [ -n "${1:-}" ] && f+=(--filter "label=arbor.grove.item=$1")
  docker ps -a "${f[@]}" --format '{{.Names}}'
}

# safe_file <path> <max bytes>: a regular file (not a symlink) no larger than the cap.
safe_file() {
  [ -f "$1" ] && [ ! -L "$1" ] || return 1
  [ "$(wc -c < "$1" | tr -d ' ')" -le "$2" ]
}

# force_rm <dir>: removes a directory the agent wrote into. On Linux the agent's files belong to
# uid 1000, so when the host user cannot remove them a throwaway container (as 1000) does.
force_rm() {
  [ -e "$1" ] || return 0
  rm -rf "$1" 2>/dev/null && return 0
  docker run --rm --network none --user 1000:1000 -v "$1:/x" --entrypoint sh "$AGENT_IMAGE" \
    -c 'rm -rf /x/* /x/.[!.]* /x/..?*' >/dev/null 2>&1 || true
  rm -rf "$1"
}

STATE="$GD/state.json"
# state_update <jq filter> [jq args...]: rewrites state.json through the filter, atomically, and
# only when the result is still a state object.
state_update() {
  local f="$1"; shift
  [ -f "$STATE" ] || die "no state at $STATE"
  jq "$@" "$f" "$STATE" > "$STATE.tmp" || { rm -f "$STATE.tmp"; die "state filter failed"; }
  jq -e '.items | type == "object"' "$STATE.tmp" >/dev/null || { rm -f "$STATE.tmp"; die "state filter dropped .items"; }
  mv "$STATE.tmp" "$STATE"
}
