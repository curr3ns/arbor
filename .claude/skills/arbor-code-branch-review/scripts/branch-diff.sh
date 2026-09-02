#!/usr/bin/env bash
# branch-diff.sh — collect a filtered branch diff payload for arbor-code-branch-review.
#
# Does every git call the review needs in one invocation, drops spec/generated
# noise, and writes the result to files on disk. Prints only a compact manifest
# so the caller pays tokens for the code, not for git plumbing.
set -euo pipefail

usage() {
  cat <<'USAGE'
branch-diff.sh [options]

  --base <ref>       Diff against <ref> instead of inferring the fork point.
  --remote           Diff the local branch against its upstream (@{u}).
  --range <A..B>     Use an explicit range verbatim. Also accepted positionally.
  --out <dir>        Write the payload here (default: a fresh mktemp -d).
  --include <glob>   Re-admit paths the exclusion rules would drop. Repeatable.
  --context <n>      Diff context lines (default 5).
  --max-bytes <n>    Split the patch into parts at this size (default 60000).
  --stat-only        Skip patch generation; emit commits, files, and skips only.
  -h, --help         This text.

Writes manifest.txt, commits.txt, files.tsv, skipped.tsv, and diff.partN.patch
into the output directory, and echoes the manifest to stdout.
USAGE
}

BASE_REF=""; USE_REMOTE=0; RANGE=""; OUT=""; CTX=5; MAX_BYTES=60000; STAT_ONLY=0
INCLUDES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --base)      BASE_REF="${2:-}"; shift 2 ;;
    --remote)    USE_REMOTE=1; shift ;;
    --range)     RANGE="${2:-}"; shift 2 ;;
    --out)       OUT="${2:-}"; shift 2 ;;
    --include)   INCLUDES+=("${2:-}"); shift 2 ;;
    --context)   CTX="${2:-}"; shift 2 ;;
    --max-bytes) MAX_BYTES="${2:-}"; shift 2 ;;
    --stat-only) STAT_ONLY=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *..*)        RANGE="$1"; shift ;;
    *)           echo "branch-diff.sh: unknown argument '$1'" >&2; usage >&2; exit 2 ;;
  esac
done

git rev-parse --git-dir >/dev/null 2>&1 || { echo "branch-diff.sh: not a git repository" >&2; exit 1; }
git config --local core.quotepath false >/dev/null 2>&1 || true

HEAD_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"

# ---------------------------------------------------------------- base resolution
BASE_NOTE=""
RUNNERS_UP=""

resolve_base() {
  # Score every plausible base by how many commits HEAD has on top of the merge
  # base. The branch this one actually forked from has the fewest; a candidate
  # that shares no unique history with HEAD scores 0 and is not a fork point.
  local prio=0 cand mb count best_score=-1 best="" ref
  local -a scored=()
  for cand in development develop main master trunk \
              origin/development origin/develop origin/main origin/master origin/trunk; do
    prio=$((prio + 1))
    ref="$(git rev-parse --verify --quiet "$cand^{commit}" 2>/dev/null)" || continue
    [ "$cand" = "$HEAD_BRANCH" ] && continue
    [ "$ref" = "$(git rev-parse HEAD)" ] && continue
    mb="$(git merge-base HEAD "$cand" 2>/dev/null)" || continue
    count="$(git rev-list --count "$mb..HEAD" 2>/dev/null || echo 0)"
    [ "$count" -eq 0 ] && continue
    scored+=("$count $prio $cand")
  done
  [ ${#scored[@]} -eq 0 ] && return 1
  local sorted
  sorted="$(printf '%s\n' "${scored[@]}" | sort -k1,1n -k2,2n)"
  best="$(printf '%s\n' "$sorted" | head -1 | cut -d' ' -f3)"
  best_score="$(printf '%s\n' "$sorted" | head -1 | cut -d' ' -f1)"
  RUNNERS_UP="$(printf '%s\n' "$sorted" | tail -n +2 | awk '{printf "%s (%s ahead), ", $3, $1}' | sed 's/, $//')"
  BASE_NOTE="inferred fork point: HEAD is $best_score commit(s) ahead of $best"
  BASE_REF="$best"
}

if [ -n "$RANGE" ]; then
  BASE_NOTE="explicit range"
elif [ -n "$BASE_REF" ]; then
  git rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null \
    || { echo "branch-diff.sh: base ref '$BASE_REF' not found" >&2; exit 1; }
  RANGE="$BASE_REF...HEAD"
  BASE_NOTE="explicit --base"
elif [ "$USE_REMOTE" -eq 1 ]; then
  UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)" \
    || { echo "branch-diff.sh: '$HEAD_BRANCH' has no upstream; push it or pass --base" >&2; exit 1; }
  RANGE="$UPSTREAM...HEAD"
  BASE_NOTE="upstream of $HEAD_BRANCH"
else
  resolve_base \
    || { echo "branch-diff.sh: could not infer a base branch; pass --base <ref> or a range" >&2; exit 1; }
  RANGE="$BASE_REF...HEAD"
fi

# Split the range so the commit log always walks forward from the merge base,
# even when the diff itself is three-dot.
LEFT="${RANGE%%.*}"
RIGHT="${RANGE##*.}"
[ -z "$RIGHT" ] && RIGHT="HEAD"
[ -z "$LEFT" ] && LEFT="HEAD"
if [ "$RANGE" = "${RANGE/.../}" ]; then
  LOG_SPEC="$RANGE"                       # two-dot: already forward-only
else
  MB="$(git merge-base "$LEFT" "$RIGHT" 2>/dev/null || echo "$LEFT")"
  LOG_SPEC="$MB..$RIGHT"
fi
MERGE_BASE="$(git merge-base "$LEFT" "$RIGHT" 2>/dev/null || git rev-parse "$LEFT")"

# ---------------------------------------------------------------- output dir
if [ -z "$OUT" ]; then OUT="$(mktemp -d "${TMPDIR:-/tmp}/branch-review.XXXXXX")"; fi
mkdir -p "$OUT"
rm -f "$OUT"/diff.part*.patch "$OUT/files.tsv" "$OUT/skipped.tsv" "$OUT/commits.txt"

git log --no-merges --format='%h %an %ad %s' --date=short "$LOG_SPEC" > "$OUT/commits.txt" 2>/dev/null || : > "$OUT/commits.txt"
COMMIT_COUNT="$(wc -l < "$OUT/commits.txt" | tr -d ' ')"

# ---------------------------------------------------------------- classification
# Normalises git's two rename spellings ("a => b" and "src/{a => b}/f") down to
# the old and new path, so numstat and name-status can be joined on one key.
NORMALIZE_AWK='
function side(p, want,   pre, suf, mid, part) {
  if (p !~ / => /) return p
  if (p ~ /\{.* => .*\}/) {
    pre = p; sub(/\{.*/, "", pre)
    suf = p; sub(/.*\}/, "", suf)
    mid = p; sub(/^[^{]*\{/, "", mid); sub(/\}[^}]*$/, "", mid)
    part = mid
    if (want == "new") sub(/^.* => /, "", part); else sub(/ => .*$/, "", part)
    p = pre part suf
    gsub(/\/\//, "/", p)
    return p
  }
  part = p
  if (want == "new") sub(/^.* => /, "", part); else sub(/ => .*$/, "", part)
  return part
}'

git diff --numstat --find-renames "$RANGE" 2>/dev/null \
  | awk -F'\t' "$NORMALIZE_AWK"'
      { print side($3,"new") "\t" $1 "\t" $2 "\t" side($3,"old") }' > "$OUT/.numstat.tsv" || : > "$OUT/.numstat.tsv"

git diff --name-status --find-renames "$RANGE" 2>/dev/null \
  | awk -F'\t' "$NORMALIZE_AWK"'
      { if (NF >= 3) print side($3,"new") "\t" $1; else print side($2,"new") "\t" $1 }' > "$OUT/.status.tsv" || : > "$OUT/.status.tsv"

is_excluded() {
  case "$1" in
    openspec/*|*/openspec/*|.openspec/*)                 echo spec; return 0 ;;
    .kiro/*|*/.kiro/*|specs/*|*/specs/*)                 echo spec; return 0 ;;
    docs/*|*/docs/*|doc/*|*/doc/*|*.rst|*.adoc)          echo docs; return 0 ;;
    README*|*/README*|CHANGELOG*|*/CHANGELOG*)           echo docs; return 0 ;;
    CONTRIBUTING*|*/CONTRIBUTING*|LICENSE*|*/LICENSE*)   echo docs; return 0 ;;
    CODE_OF_CONDUCT*|SECURITY.md|*/SECURITY.md)          echo docs; return 0 ;;
    *.lock|package-lock.json|*/package-lock.json)        echo lockfile; return 0 ;;
    yarn.lock|*/yarn.lock|pnpm-lock.yaml|*/pnpm-lock.yaml) echo lockfile; return 0 ;;
    go.sum|*/go.sum|*.lockb)                             echo lockfile; return 0 ;;
    dist/*|*/dist/*|build/*|*/build/*|out/*|*/out/*)     echo generated; return 0 ;;
    target/*|*/target/*|vendor/*|*/vendor/*)             echo generated; return 0 ;;
    node_modules/*|*/node_modules/*|.next/*|*/.next/*)   echo generated; return 0 ;;
    *.min.js|*.min.css|*.map)                            echo generated; return 0 ;;
    *__snapshots__/*|*.snap)                             echo generated; return 0 ;;
    *.generated.*|*_pb2.py|*_pb2_grpc.py|*.pb.go)        echo generated; return 0 ;;
    *.g.dart|*.freezed.dart|*.designer.cs)               echo generated; return 0 ;;
    *.png|*.jpg|*.jpeg|*.gif|*.svg|*.ico|*.webp|*.pdf)   echo asset; return 0 ;;
    *.zip|*.gz|*.tgz|*.jar|*.woff|*.woff2|*.ttf|*.mp4)   echo asset; return 0 ;;
  esac
  return 1
}

force_included() {
  local p="$1" pat
  for pat in ${INCLUDES+"${INCLUDES[@]}"}; do
    # Unquoted RHS: bash treats it as a glob pattern, which is what we want.
    [[ $p == $pat ]] && return 0
  done
  return 1
}

KEPT_FILE="$OUT/.kept.txt"; : > "$KEPT_FILE"
: > "$OUT/files.tsv"; : > "$OUT/skipped.tsv"
printf 'status\tadded\tdeleted\tpath\trenamed_from\n' >> "$OUT/files.tsv"
printf 'reason\tadded\tdeleted\tpath\n' >> "$OUT/skipped.tsv"

TOTAL_ADD=0; TOTAL_DEL=0; KEPT_N=0; SKIPPED_N=0
while IFS=$'\t' read -r path add del oldpath; do
  [ -z "$path" ] && continue
  status="$(awk -F'\t' -v p="$path" '$1 == p { print $2; exit }' "$OUT/.status.tsv")"
  [ -z "$status" ] && status="M"
  reason=""
  if [ "$add" = "-" ] || [ "$del" = "-" ]; then
    reason="binary"; add=0; del=0
  elif reason_out="$(is_excluded "$path")"; then
    reason="$reason_out"
  fi
  if [ -n "$reason" ] && force_included "$path"; then reason=""; fi
  if [ -n "$reason" ]; then
    printf '%s\t%s\t%s\t%s\n' "$reason" "$add" "$del" "$path" >> "$OUT/skipped.tsv"
    SKIPPED_N=$((SKIPPED_N + 1))
  else
    [ "$path" = "$oldpath" ] && oldpath=""
    printf '%s\t%s\t%s\t%s\t%s\n' "$status" "$add" "$del" "$path" "$oldpath" >> "$OUT/files.tsv"
    printf '%s\n' "$path" >> "$KEPT_FILE"
    TOTAL_ADD=$((TOTAL_ADD + add)); TOTAL_DEL=$((TOTAL_DEL + del))
    KEPT_N=$((KEPT_N + 1))
  fi
done < "$OUT/.numstat.tsv"

# ---------------------------------------------------------------- patch, split on file boundaries
PARTS=0
if [ "$STAT_ONLY" -eq 0 ] && [ "$KEPT_N" -gt 0 ]; then
  PARTS=1; part="$OUT/diff.part1.patch"; : > "$part"
  while IFS= read -r p; do
    tmp="$OUT/.one.patch"
    git diff --find-renames -U"$CTX" "$RANGE" -- "$p" > "$tmp" 2>/dev/null || : > "$tmp"
    [ -s "$tmp" ] || continue
    cur=$(wc -c < "$part" | tr -d ' ')
    one=$(wc -c < "$tmp" | tr -d ' ')
    if [ "$cur" -gt 0 ] && [ $((cur + one)) -gt "$MAX_BYTES" ]; then
      PARTS=$((PARTS + 1)); part="$OUT/diff.part${PARTS}.patch"; : > "$part"
    fi
    cat "$tmp" >> "$part"
  done < "$KEPT_FILE"
  rm -f "$OUT/.one.patch"
  # A trailing empty part can happen if the last file produced no hunks.
  [ -s "$OUT/diff.part${PARTS}.patch" ] || { rm -f "$OUT/diff.part${PARTS}.patch"; PARTS=$((PARTS - 1)); }
fi

rm -f "$OUT/.numstat.tsv" "$OUT/.status.tsv" "$KEPT_FILE"

DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"

# ---------------------------------------------------------------- manifest
{
  echo "branch:        $HEAD_BRANCH"
  echo "range:         $RANGE"
  echo "base:          ${BASE_REF:-$LEFT}  ($BASE_NOTE)"
  echo "merge_base:    $MERGE_BASE"
  [ -n "$RUNNERS_UP" ] && echo "other_bases:   $RUNNERS_UP"
  echo "commits:       $COMMIT_COUNT"
  echo "files_kept:    $KEPT_N  (+$TOTAL_ADD / -$TOTAL_DEL)"
  echo "files_skipped: $SKIPPED_N"
  echo "patch_parts:   $PARTS"
  [ "$DIRTY" -gt 0 ] && echo "warning:       $DIRTY uncommitted change(s) in the working tree are NOT included"
  [ "$KEPT_N" -eq 0 ] && echo "warning:       no reviewable code changed in this range"
  echo "out:           $OUT"
} | tee "$OUT/manifest.txt"
