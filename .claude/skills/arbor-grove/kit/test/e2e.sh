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
jq -n --arg name "$NAME" '{grove: {name: $name, default_branch: "main", verify: "sh check.sh", registries: []}}' > "$T/repo/.arbor/config.json"
printf 'fake-credential' > "$GROVE_CREDENTIAL_FILE"; chmod 600 "$GROVE_CREDENTIAL_FILE"

"$BIN/grove-build" >/dev/null
docker build -q -t "$GROVE_AGENT_IMAGE" "$KIT/test/fake" >/dev/null
pass "images built"

"$BIN/grove-mirror" >/dev/null
pass "mirror"

items="$T/repo/.arbor/grove/items"
mkdir -p "$items/gh-1/in"
jq -n '{mode: "work", item: {id: "gh-1", title: "Add hello", body: "Add hello.txt", url: null},
  repo: {default_branch: "main", verify: "sh check.sh"}, branch: "grove/gh-1", model: "sonnet",
  criteria: ["hello.txt exists"], footprint: {globs: ["hello.txt"], whole_repo: false}, peers: [],
  limits: {verify_attempts: 3, cr_wait_minutes: 1}, resume: null}' > "$items/gh-1/in/task.json"
echo '{"globs": ["hello.txt"], "whole_repo": false}' > "$items/gh-1/footprint.json"

"$BIN/grove-watch" > "$T/events" 2>&1 & watch_pid=$!
read -r agent run < <("$BIN/grove-launch" gh-1 work)
[ "$(docker wait "$agent")" = 0 ] || { docker logs "$agent" >&2; fail "agent container exit"; }
result="$("$BIN/grove-read" gh-1 result.json)"
[ "$(jq -r .outcome <<<"$result")" = handoff ] || { cat "$items/gh-1/out/claude.stderr" >&2; fail "outcome: $result"; }
[ "$(jq -r .verify.passed <<<"$result")" = true ] || fail "entrypoint verify: $result"
[ "$(jq -r .verify.exit <<<"$result")" = 0 ] || fail "verify exit was forged or wrong: $result"
pass "work run hands off through relay and egress, verify passes"

"$BIN/grove-read" gh-1 handoff.md | grep -q 'hello.txt:1' || fail "handoff"
ln -s /etc/passwd "$items/gh-1/out/evil"
"$BIN/grove-read" gh-1 evil >/dev/null && fail "grove-read followed a symlink"
pass "grove-read refuses symlinks"

sleep 3
grep -q "^exit gh-1 $run work$" "$T/events" || { cat "$T/events" >&2; fail "no exit event"; }
grep -q "^mail gh-1 $run 000001-status.json$" "$T/events" || { cat "$T/events" >&2; fail "no mail event"; }
mkdir -p "$T/repo/.arbor/grove/answers" && echo "use blue" > "$T/repo/.arbor/grove/answers/gh-1.md"
echo drain > "$T/repo/.arbor/grove/stop"
sleep 3
grep -q '^answer gh-1$' "$T/events" || { cat "$T/events" >&2; fail "no answer event"; }
grep -q '^stop drain$' "$T/events" || { cat "$T/events" >&2; fail "no stop event"; }
rm -f "$T/repo/.arbor/grove/stop"
pass "watch reports exit, mail, answer and stop"

echo '{"type":"notice","id":"m1","from":"grove","text":"hi"}' | "$BIN/grove-deliver" gh-1 >/dev/null
[ -f "$items/gh-1/in/inbox/000001-notice.json" ] || fail "deliver"
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
echo "Add hello.txt (#1)" > "$T/msg"
prep="$("$BIN/grove-land" prepare gh-1 "$head" "$T/msg")"
[ "$(jq -r .status <<<"$prep")" = ok ] && [ "$(jq -r .changed <<<"$prep")" = false ] || fail "prepare: $prep"
pass "rebase onto a moved default branch, diff unchanged"

jq -n '{mode: "regate", ref: "refs/grove/rebased/gh-1", repo: {verify: "sh check.sh"}}' > "$items/gh-1/in/task.json"
read -r agent run < <("$BIN/grove-launch" gh-1 regate)
docker wait "$agent" >/dev/null
[ "$("$BIN/grove-read" gh-1 result.json | jq -r .passed)" = true ] || fail "regate"
[ ! -e "$items/gh-1/secret" ] || fail "regate got a credential"
"$BIN/grove-teardown" gh-1 >/dev/null
pass "regate passes without a credential"

[ "$(jq -r .status <<<"$("$BIN/grove-land" push gh-1)")" = pushed ] || fail "push"
git -C "$T/origin.git" log -1 --format=%s main | grep -qx "Add hello.txt (#1)" || fail "origin head"
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
