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

# e2e_project <item>: the compose project grove-host-verify runs the item's stack under.
e2e_project() { printf 'arbor-grove-%s-%s-e2e' "$NAME" "$1"; }
# prune_e2e <item>: removes what the item's host-verify stack left behind — its containers and the
# images compose built for it — by the compose project label, so nothing outside that project is
# touched. Pulled images (a database, say) carry no project label and stay.
prune_e2e() {
  local f=(--filter "label=com.docker.compose.project=$(e2e_project "$1")") ids
  ids="$(docker ps -aq "${f[@]}" 2>/dev/null)" || return 0
  # shellcheck disable=SC2086 # one id per word
  [ -z "$ids" ] || docker rm -f $ids >/dev/null 2>&1 || true
  ids="$(docker image ls -q "${f[@]}" 2>/dev/null | sort -u)" || return 0
  # shellcheck disable=SC2086
  [ -z "$ids" ] || docker image rm -f $ids >/dev/null 2>&1 || true
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

# host_guarded <base> <head> <approved json>: files changed between base and head (in the mirror)
# that match a grove.host_verify.guard pattern — bash patterns, where `*` also matches `/` — and
# whose content at head is not one approved ({path: [blob, ...]}; "deleted" for a removed file).
# These are the files grove-host-verify would hand to the host's Docker daemon. One path per line.
host_guarded() {
  local base="$1" head="$2" approved="$3" patterns f p blob
  patterns="$(jq -r '.grove.host_verify.guard[]? | strings' "$CONFIG" 2>/dev/null || true)"
  [ -n "$patterns" ] || return 0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    while IFS= read -r p; do
      # shellcheck disable=SC2053 # $p is a pattern on purpose
      [[ "$f" == $p ]] || continue
      blob="$(git -C "$MIRROR" rev-parse -q --verify "$head:$f" 2>/dev/null || echo deleted)"
      jq -e --arg f "$f" --arg b "$blob" '.[$f] // [] | index($b) != null' <<<"$approved" >/dev/null \
        || printf '%s\n' "$f"
      break
    done <<<"$patterns"
  done < <(git -C "$MIRROR" diff --name-only --no-renames "$base" "$head")
}

STATE="$GD/state.json"
# guard_approved <item>: the item's human-approved guarded files, {path: [blob, ...]} ({} when none).
guard_approved() {
  [ -f "$STATE" ] || { echo '{}'; return; }
  jq -c --arg id "$1" '.items[$id].guard_approved // {}' "$STATE"
}
# state_update <jq filter> [jq args...]: rewrites state.json through the filter, atomically, and
# only when the result is still a state object.
state_update() {
  local f="$1"; shift
  [ -f "$STATE" ] || die "no state at $STATE"
  jq "$@" "$f" "$STATE" > "$STATE.tmp" || { rm -f "$STATE.tmp"; die "state filter failed"; }
  jq -e '.items | type == "object"' "$STATE.tmp" >/dev/null || { rm -f "$STATE.tmp"; die "state filter dropped .items"; }
  mv "$STATE.tmp" "$STATE"
}
