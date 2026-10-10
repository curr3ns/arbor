#!/usr/bin/env bash
# End-to-end test of the grove kit against a real Docker daemon, with a stub `claude` (test/fake):
# images, mirror, launch through the egress proxy, watch events, harvest checks, rebase and squash,
# re-gate, push, mail delivery, and the checks that park bad changes. Needs docker, git and jq.
# Leaves nothing behind but the built images.
set -euo pipefail
KIT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$KIT/bin"
pass() { echo "ok   $*"; }
fail() { echo "FAIL $*" >&2; exit 1; }

T="$(mktemp -d "${TMPDIR:-/tmp}/grove-e2e.XXXXXX")"
T="$(cd "$T" && pwd -P)" # Docker Desktop shares /private/var, not the /var symlink
export GROVE_REPO="$T/repo" GROVE_CREDENTIAL_FILE="$T/credential" GROVE_AGENT_IMAGE=arbor-grove-agent-test:latest
export GROVE_WATCH_INTERVAL=1
NAME="e2e-$$"
watch_pid=""
cleanup() {
  if [ -n "$watch_pid" ]; then kill "$watch_pid" 2>/dev/null || true; wait "$watch_pid" 2>/dev/null || true; fi
  for i in gh-1 gh-2; do "$BIN/grove-teardown" "$i" >/dev/null 2>&1 || true; done
  rm -rf "$T"
}
trap cleanup EXIT

git_q() { git -c init.defaultBranch=main -c user.name=t -c user.email=t@t "$@"; }

# origin: a bare repo whose verification command needs hello.txt
git_q init -q "$T/seed"
printf 'test -f hello.txt\n' > "$T/seed/check.sh"
echo readme > "$T/seed/README.md"
git_q -C "$T/seed" add -A && git_q -C "$T/seed" commit -qm init
git clone -q --bare "$T/seed" "$T/origin.git"
git clone -q "$T/origin.git" "$T/repo"
mkdir -p "$T/repo/.arbor"
jq -n --arg name "$NAME" '{grove: {name: $name, default_branch: "main", verify: "sh check.sh", registries: [],
  limits: {cr_wait_minutes: 1}}}' > "$T/repo/.arbor/config.json"
printf 'fake-credential' > "$GROVE_CREDENTIAL_FILE"; chmod 600 "$GROVE_CREDENTIAL_FILE"

"$BIN/grove-build" >/dev/null
docker build -q -t "$GROVE_AGENT_IMAGE" "$KIT/test/fake" >/dev/null
pass "images built"

"$BIN/grove-mirror" >/dev/null
pass "mirror"

items="$T/repo/.arbor/grove/items"
"$BIN/grove-state" start >/dev/null
# source jira: grove-admit leaves the claim to the session, so the test needs no GitHub
"$BIN/grove-state" '.items["gh-1"] = {source: "jira", key: "E2E-1", title: "Add hello",
  body: "Add hello.txt", url: null, state: "ready", criteria: ["hello.txt exists"],
  footprint: {globs: ["hello.txt"], whole_repo: false}, grants: [], run: null, wip: false, notes: ""}' >/dev/null
"$BIN/grove-state" 'del(.items)' >/dev/null 2>&1 && fail "grove-state let a filter drop .items"
pass "grove-state"

"$BIN/grove-watch" > "$T/events" 2>&1 & watch_pid=$!
admitted="$("$BIN/grove-admit" gh-1)"
[ "$(jq -r .state <<<"$admitted")" = running ] || fail "admit: $admitted"
run="$(jq -r .run <<<"$admitted")"; agent="arbor-grove-$NAME-gh-1-agent"
[ "$(jq -c '[.mode, .branch, .resume, .limits.cr_wait_minutes, .footprint.globs]' "$items/gh-1/in/task.json")" \
  = '["work","grove/gh-1",null,1,["hello.txt"]]' ] || fail "admit task: $(cat "$items/gh-1/in/task.json")"
[ "$(docker wait "$agent")" = 0 ] || { docker logs "$agent" >&2; fail "agent container exit"; }
result="$("$BIN/grove-read" gh-1 result.json)"
[ "$(jq -r .outcome <<<"$result")" = handoff ] || { cat "$items/gh-1/out/claude.stderr" >&2; fail "outcome: $result"; }
[ "$(jq -r .verify.passed <<<"$result")" = true ] || fail "entrypoint verify: $result"
[ "$(jq -r .verify.exit <<<"$result")" = 0 ] || fail "verify exit was forged or wrong: $result"
pass "admit launches a work run that hands off through relay and egress, verify passes"

"$BIN/grove-read" gh-1 handoff.md | grep -q 'hello.txt:1' || fail "handoff"
ln -s /etc/passwd "$items/gh-1/out/evil"
"$BIN/grove-read" gh-1 evil >/dev/null && fail "grove-read followed a symlink"
pass "grove-read refuses symlinks"

# wait_event <line>: up to 20 s for the watcher to print it
wait_event() { for _ in $(seq 40); do grep -qx "$1" "$T/events" && return 0; sleep 0.5; done; return 1; }
wait_event "exit gh-1 $run work" || { cat "$T/events" >&2; fail "no exit event"; }
wait_event "mail gh-1 $run 000001-status.json" || { cat "$T/events" >&2; fail "no mail event"; }
echo "use blue" | "$BIN/grove-signal" answer gh-1 >/dev/null
"$BIN/grove-signal" stop drain >/dev/null
wait_event "answer gh-1" || { cat "$T/events" >&2; fail "no answer event"; }
wait_event "stop drain" || { cat "$T/events" >&2; fail "no stop event"; }
[ "$("$BIN/grove-signal" take gh-1)" = "use blue" ] || fail "signal take"
[ ! -e "$T/repo/.arbor/grove/answers/gh-1.md" ] || fail "signal take left the answer"
"$BIN/grove-signal" clear >/dev/null
pass "watch reports exit, mail, answer and stop"

[ "$("$BIN/grove-deliver" gh-1 <<<'{"type":"notice","from":"grove","text":"hi"}')" = "000001-notice.json m1" ] || fail "deliver"
[ "$(jq -r .next_message "$T/repo/.arbor/grove/state.json")" = 2 ] || fail "deliver did not advance next_message"
echo '{"type":"evil","id":"m2"}' | "$BIN/grove-deliver" gh-1 2>/dev/null && fail "deliver accepted an unknown type"
pass "deliver"

report="$("$BIN/grove-harvest" gh-1)"
[ "$(jq -r .clean <<<"$report")" = true ] || fail "harvest not clean: $report"
[ "$(jq -c .files <<<"$report")" = '["hello.txt"]' ] || fail "harvest files: $report"
head="$(jq -r .head <<<"$report")"
pass "harvest clean"

"$BIN/grove-teardown" gh-1 >/dev/null
[ -z "$(docker ps -aq --filter "label=arbor.grove=$NAME")" ] || fail "teardown left containers"
pass "teardown"

# origin moves on, in a file the item does not touch: the rebase must not count as a change
git clone -q "$T/origin.git" "$T/other"
echo more >> "$T/other/README.md"
git_q -C "$T/other" commit -qam "Unrelated" && git -C "$T/other" push -q origin main
msg="$("$BIN/grove-message" gh-1)"
head -1 "$msg" | grep -qx 'E2E-1: Add hello' || fail "message: $(cat "$msg")"
prep="$("$BIN/grove-land" prepare gh-1 "$head" "$msg")"
[ "$(jq -r .status <<<"$prep")" = ok ] && [ "$(jq -r .changed <<<"$prep")" = false ] || fail "prepare: $prep"
pass "rebase onto a moved default branch, diff unchanged"

"$BIN/grove-state" '.items["gh-1"].state = "merging"' >/dev/null
"$BIN/grove-regate" gh-1 >/dev/null
docker wait "$agent" >/dev/null
[ "$("$BIN/grove-read" gh-1 result.json | jq -r .passed)" = true ] || fail "regate"
[ ! -e "$items/gh-1/secret" ] || fail "regate got a credential"
"$BIN/grove-teardown" gh-1 >/dev/null
pass "regate passes without a credential"

[ "$(jq -r .status <<<"$("$BIN/grove-land" push gh-1)")" = pushed ] || fail "push"
git -C "$T/origin.git" log -1 --format=%s main | grep -qx "E2E-1: Add hello" || fail "origin head"
git -C "$T/origin.git" cat-file -e main:hello.txt || fail "hello.txt on origin"
pass "squashed push to origin"

# A change the gate must never see: protected path, symlink, secret, outside the footprint
git clone -q "$T/origin.git" "$T/bad" && git -C "$T/bad" checkout -qb grove/gh-2
mkdir -p "$T/bad/.github" && echo x > "$T/bad/.github/ci.yml"
ln -s /etc/passwd "$T/bad/link"
echo "token = ghp_$(printf 'a%.0s' $(seq 1 36))" > "$T/bad/conf.txt"
git_q -C "$T/bad" add -A && git_q -C "$T/bad" commit -qm bad
mkdir -p "$items/gh-2/out" && git -C "$T/bad" bundle create -q "$items/gh-2/out/branch.bundle" grove/gh-2
echo '{"globs": ["src/**"], "whole_repo": false}' > "$items/gh-2/footprint.json"
r="$("$BIN/grove-harvest" gh-2)"
[ "$(jq -r .clean <<<"$r")" = false ] || fail "bad change passed: $r"
jq -e '(.protected == [".github/ci.yml"]) and (.symlink == ["link"]) and (.secrets == ["conf.txt"])
       and (.outside_footprint | length == 3)' <<<"$r" >/dev/null || fail "harvest flags: $r"
pass "harvest flags protected path, symlink, secret and footprint"

echo "all e2e checks passed"
