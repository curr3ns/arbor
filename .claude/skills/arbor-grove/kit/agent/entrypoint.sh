#!/bin/sh
# The agent container's entrypoint (reference/protocol.md). It does everything that must not depend
# on the model: the egress relay, the repo checkout, the heartbeat, committing what the agent left,
# the branch bundle, the final verification run without a credential, and the one result.json the
# hypervisor reads. The work itself is the arbor-grove-agent skill, run by `claude -p`.
#
# GROVE_MODE=work (default) runs the agent; GROVE_MODE=regate only runs the verification command on
# a ref from the bundle, with no Claude credential mounted or exported.
set -eu

mode="${GROVE_MODE:-work}"
in="${GROVE_IN_DIR:-/exchange/in}"
out="${GROVE_OUT_DIR:-/exchange/out}"
secret=/run/grove-secret/claude
task="$in/task.json"
repo=/workspace/repo
work=/workspace/.grove-work # outside the repo, so nothing here can be committed

KIB=1024
cap() { head -c "$1"; } # cap stdin at $1 bytes

# result <json>: the only writer of out/result.json. Anything the agent left there is replaced.
result() {
  rm -rf "$out/result.json" "$out/.result.json.tmp"
  printf '%s\n' "$1" > "$out/.result.json.tmp"
  mv "$out/.result.json.tmp" "$out/result.json"
}

case "$mode" in work|regate) ;; *) echo "grove-agent: unknown GROVE_MODE $mode" >&2; exit 1 ;; esac
[ -r "$task" ] || { echo "grove-agent: cannot read $task" >&2; exit 1; }
task_mode=$(jq -r '.mode' "$task")
if [ "$task_mode" != "$mode" ]; then
  # A work-mode credential must never reach a re-gate's repo-controlled verify command, and back.
  echo "grove-agent: GROVE_MODE=$mode but task.json mode=$task_mode" >&2
  exit 1
fi
if [ "$mode" = work ]; then
  [ -r "$secret" ] || { echo "grove-agent: cannot read $secret" >&2; exit 1; }
  : "${GROVE_CREDENTIAL_ENV:?grove-agent: GROVE_CREDENTIAL_ENV is not set}"
  case "$GROVE_CREDENTIAL_ENV" in ANTHROPIC_API_KEY|CLAUDE_CODE_OAUTH_TOKEN) ;; *)
    echo "grove-agent: GROVE_CREDENTIAL_ENV must be ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN" >&2; exit 1 ;;
  esac
fi

# The container has no network: the relay on 127.0.0.1:3128 is the only way out, to the egress
# proxy's socket. The work starts only once the relay itself wrote its pid to a marker on this
# container's own /tmp after its listen succeeded, and is still alive.
relay_js="${GROVE_RELAY_JS:-/opt/grove/relay.ts}"
ready_file="${GROVE_RELAY_READY:-/tmp/grove-relay.ready}"
export GROVE_RELAY_READY="$ready_file"
if [ "${GROVE_NO_RELAY:-}" != 1 ]; then
  node "$relay_js" &
  relay_pid=$!
  ready=no
  for _ in $(seq 1 50); do
    if [ -f "$ready_file" ] && [ "$(cat "$ready_file")" = "$relay_pid" ] && kill -0 "$relay_pid" 2>/dev/null; then
      ready=yes
      break
    fi
    kill -0 "$relay_pid" 2>/dev/null || break
    sleep 0.1
  done
  if [ "$ready" != yes ]; then
    kill "$relay_pid" 2>/dev/null || true
    echo "grove-agent: the egress relay did not report listening on 127.0.0.1:3128 within 5s" >&2
    exit 1
  fi
fi

# A plain environment for every repo-controlled command: no credential of any kind.
scrub() {
  env -u ANTHROPIC_API_KEY -u CLAUDE_CODE_OAUTH_TOKEN -u GITHUB_TOKEN -u GH_TOKEN -u JIRA_API_TOKEN -u GROVE_CREDENTIAL_ENV "$@"
}

# verify <dir>: runs the repo's verification command there, credential-free; sets verify_rc.
verify() {
  cmd=$(jq -r '.repo.verify' "$task")
  set +e
  (cd "$1" && scrub sh -c "$cmd") > "$out/.verify.log" 2>&1
  verify_rc=$?
  set -e
  tail -c $((32 * KIB)) "$out/.verify.log" > "$out/verify.log"
  rm -f "$out/.verify.log"
}

if [ "$mode" = regate ]; then
  ref=$(jq -r '.ref' "$task")
  case "$ref" in refs/grove/rebased/*) ;; *) echo "grove-agent: refusing re-gate ref $ref" >&2; exit 1 ;; esac
  mkdir -p "$repo"
  git -C "$repo" init -q -b regate-base
  git -C "$repo" fetch -q "$in/repo.bundle" "+$ref:refs/heads/regate"
  git -C "$repo" checkout -q regate
  verify "$repo"
  passed=false; [ "$verify_rc" = 0 ] && passed=true
  result "$(jq -cn --argjson passed "$passed" --argjson exit "$verify_rc" '{outcome: "regate", passed: $passed, exit: $exit}')"
  exit 0
fi

# --- work mode ---
item=$(jq -r '.item.id' "$task")
base=$(jq -r '.repo.default_branch' "$task")
branch=$(jq -r '.branch' "$task")
resume_ref=$(jq -r '.resume.ref // empty' "$task")
model=$(jq -r '.model // "sonnet"' "$task")
case "$branch" in grove/*) ;; *) echo "grove-agent: refusing branch $branch" >&2; exit 1 ;; esac

git clone -q --branch "$base" "$in/repo.bundle" "$repo"
cd "$repo"
if [ -n "$resume_ref" ]; then
  [ "$resume_ref" = "refs/grove/wip/$item" ] || { echo "grove-agent: refusing resume ref $resume_ref" >&2; exit 1; }
  git fetch -q "$in/repo.bundle" "+$resume_ref:refs/heads/$branch"
  git checkout -q "$branch"
else
  git checkout -q -b "$branch"
fi
git config user.name grove-agent
git config user.email grove-agent@localhost
base_sha=$(git rev-parse "refs/heads/$base")
mkdir -p "$work"
printf '%s\n' "$base_sha" > "$work/base"

commits() { git rev-list --count "$base_sha..refs/heads/$branch"; }

# If the agent left another branch checked out or a detached HEAD, bring the task branch back,
# moving it forward only when that keeps its commits.
ensure_branch() {
  head=$(git symbolic-ref -q HEAD || true)
  if [ "$head" != "refs/heads/$branch" ]; then
    if git merge-base --is-ancestor "refs/heads/$branch" HEAD 2>/dev/null; then git branch -f "$branch" HEAD; fi
    git checkout -q -f "$branch"
  fi
}

# Atomic: the hypervisor may import out/branch.bundle after a timeout or a crash.
write_bundle() {
  rm -rf "$out/.branch.bundle.tmp"
  git bundle create -q "$out/.branch.bundle.tmp" "$branch" 2>/dev/null
  mv -f "$out/.branch.bundle.tmp" "$out/branch.bundle"
}

# Liveness that does not depend on the model: a long tool call is not a hang.
( while :; do date +%s > "$out/heartbeat"; sleep 30; done ) &
beat_pid=$!
trap 'kill "$beat_pid" 2>/dev/null || true' EXIT

# The skill is copied into this run's own HOME (a tmpfs), never baked into a shared one.
mkdir -p "$HOME/.claude/skills"
cp -R /opt/grove/skills/arbor-grove-agent "$HOME/.claude/skills/"

set +e
# Exported in a subshell rather than passed to env, so the credential never sits in a command line.
(
  export "$GROVE_CREDENTIAL_ENV=$(cat "$secret")"
  export DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
  exec "${GROVE_CLAUDE_BIN:-claude}" -p "Use the arbor-grove-agent skill to work the item described in $task." \
    --model "$model" --dangerously-skip-permissions --output-format stream-json --verbose
) > "$out/transcript.jsonl" 2> "$out/claude.stderr"
claude_rc=$?
set -e

# Commit whatever the agent left uncommitted, on the task branch.
ensure_branch
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q --no-verify -m "grove: commit changes left uncommitted by the agent"
fi
n=$(commits)
[ "$n" -gt 0 ] && write_bundle

# The handoff and question travel as files, capped; result.json carries only fixed fields.
rm -rf "$out/handoff.md" "$out/question.md"
[ -f "$work/handoff.md" ] && [ ! -L "$work/handoff.md" ] && cap $((64 * KIB)) < "$work/handoff.md" > "$out/handoff.md"
[ -f "$work/question.md" ] && [ ! -L "$work/question.md" ] && cap $((8 * KIB)) < "$work/question.md" > "$out/question.md"

agent_outcome=""
if [ -f "$work/result.json" ] && [ ! -L "$work/result.json" ]; then
  agent_outcome=$(jq -r 'if type == "object" then (.outcome // "") else "" end' "$work/result.json" 2>/dev/null || true)
fi

if grep -Eq 'authentication_error|invalid x-api-key|OAuth token (has expired|is invalid)|Invalid API key' "$out/transcript.jsonl" "$out/claude.stderr" 2>/dev/null \
  && [ -z "$agent_outcome" ]; then
  result "$(jq -cn --argjson commits "$n" '{outcome: "auth", commits: $commits}')"
  exit 0
fi

case "$agent_outcome" in
  park)
    reason=$(jq -r '.reason // "question"' "$work/result.json" | tr -cd 'a-z0-9-' | cut -c1-40)
    result "$(jq -cn --arg reason "${reason:-question}" --argjson commits "$n" '{outcome: "park", reason: $reason, commits: $commits}')"
    ;;
  handoff)
    if [ "$n" -eq 0 ]; then
      result '{"outcome":"empty-change","commits":0}'
    else
      verify "$repo"
      passed=false; [ "$verify_rc" = 0 ] && passed=true
      result "$(jq -cn --argjson passed "$passed" --argjson exit "$verify_rc" --argjson commits "$n" \
        '{outcome: "handoff", verify: {passed: $passed, exit: $exit}, commits: $commits}')"
    fi
    ;;
  *)
    tail -c $((4 * KIB)) "$out/claude.stderr" > "$out/crash.log" 2>/dev/null || true
    result "$(jq -cn --argjson rc "$claude_rc" --argjson commits "$n" '{outcome: "crash", exit: $rc, commits: $commits}')"
    ;;
esac
exit 0
