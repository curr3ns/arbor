---
name: arbor-code-branch-review
description: Summarize everything that changed on a branch relative to its base for a developer who generated the code with AI. Diffs against the inferred fork point (development by default, or any --base/--remote/range), strips OpenSpec and other spec, doc, lockfile, and generated noise, then walks the remaining code block by block — what each block does and how it hangs together — and finishes with a quick code review. Writes a Markdown report to a tmp file and opens it. Use when the user wants to understand, hand off, or sanity-check a branch of AI-written code before merging.
license: MIT
metadata:
  author: arbor
  version: "1.0"
---

# Arbor branch review

Turn a branch diff into a report a developer can actually read: what the AI
built, why each piece is there, and what is worth a second look before merge.

The audience is someone who **prompted this code into existence but did not
write it**. They need orientation, not a changelog. Explain intent and mechanism,
not just "added a function".

**Announce at start:** "Using arbor-code-branch-review to summarize this branch."

## Inputs

All optional; every one is forwarded to `scripts/branch-diff.sh`.

| Input | Effect |
|---|---|
| *(nothing)* | Infer the fork point — `development` when it exists, else `develop`/`main`/`master`/`trunk`, picking whichever the branch actually forked from. **This is the normal case.** |
| `--base <ref>` | Diff against `<ref>` instead. |
| `--remote` | Diff the local branch against its own upstream (`@{u}`) — what has not been pushed. |
| `<A>..<B>` / `<A>...<B>` | Any range `git diff` accepts, used verbatim. |
| `--include <glob>` | Re-admit a path the exclusion rules drop (repeatable). |
| `--context <n>` | Diff context lines (default 5). |

## The token rule

**Run the script once. Never re-derive its output with your own `git` calls.**

`git log`, `git diff --stat`, and a raw `git diff` cost several times what the
script's filtered payload costs, and the raw diff carries spec files, lockfiles,
and generated output you would then pay to read and discard. The script does
that work in one process and prints a manifest of about a dozen lines; the
payload sits on disk for you to read deliberately.

Do not run `git diff` yourself. Do not open the source files to "check" a hunk
unless the patch genuinely lacks the context to explain it — `-U5` is usually
enough. If you do need a file, read the specific line range, never the whole file.

## Steps

You MUST create a todo per step and complete them in order.

### 1. Collect the payload

```bash
OUT="<scratchpad>/branch-review"
~/.claude/skills/arbor-code-branch-review/scripts/branch-diff.sh --out "$OUT" <user's arguments>
```

The manifest it prints to stdout is your orientation: branch, resolved base and
why, merge base, commit count, files kept, files skipped, patch parts.

**Read the manifest before anything else.** If it warns that no reviewable code
changed, stop and report that — say which base was used and what was skipped, so
the user can tell an empty branch from a wrong base. If `other_bases` lists a
candidate the user would have expected, say so; a wrong inferred base is the one
failure mode that silently invalidates the whole report.

### 2. Read the payload

In order, from `$OUT`:

1. `commits.txt` — the branch's story in commit subjects.
2. `files.tsv` — `status`, `added`, `deleted`, `path`, `renamed_from`. Your map.
3. `diff.part1.patch`, `diff.part2.patch`, … — the code, split on file
   boundaries. **Read every part.** Parts exist to pace the reading, not to let
   you skip the tail; a review that covers part 1 and guesses at part 3 is worse
   than no review.
4. `skipped.tsv` — what was filtered, with a reason per path.

### 3. Understand before you judge

Before writing anything, work out what the branch is *for*. Read the commits and
the file map together and form a single sentence of intent. Then trace how the
changed pieces connect: what calls what, what is new surface area versus changed
internals, what the entry points are.

If the diff contradicts the commit messages, trust the diff and flag the gap.

### 4. Write the report

Write to a tmp file and open it:

```bash
REPORT=$(mktemp "${TMPDIR:-/tmp}/branch-review.XXXXXX") && mv "$REPORT" "$REPORT.md" && REPORT="$REPORT.md"
cat > "$REPORT" << 'EOF'
<report>
EOF
open "$REPORT"
```

Structure, in this order:

**1. Header.** Branch, base and how it was chosen, commit count, files and lines
changed. One line each.

**2. What this branch does.** Two to four paragraphs of plain prose. The intent
the diff adds up to, how the pieces fit together, and what a reader should hold
in their head before looking at code. No bullet lists here — this is the part
that orients someone who did not write the code.

**3. Per-file walkthrough.** For each kept file, in dependency order where you
can tell it (definitions before callers), otherwise in `files.tsv` order:

- A heading with the path and a one-line summary of the file's role.
- The changed code as fenced blocks, exactly as it would appear in review, with
  a `path:line` reference above each block. Show added and modified code; show
  deleted code only when the removal is the point.
- After each block, prose explaining **what it does, why it exists, what calls
  it, and what it depends on.** This is the core of the report — it is what the
  developer cannot get from the diff alone. Do not restate the code in English
  ("this sets `x` to 5"); explain the mechanism and the decision behind it.
- Call out anything the AI chose that a human might not have: an unusual data
  structure, a silent fallback, a new dependency, a widened interface.

**4. Review findings.** A quick but real code review over the same code,
severity-ordered, each anchored to `path:line`. Cover correctness, error and
edge-case handling, security, and reuse/simplification. Two rules:

- **Separate "this is wrong" from "this is a matter of taste."** Use explicit
  `Bug` / `Risk` / `Style` labels. An AI-written branch usually has both, and
  conflating them wastes the developer's attention on the wrong lines.
- **Every finding needs a concrete failure or a concrete improvement.** "Consider
  adding error handling" is noise; "line 42 dereferences `cfg.timeout` before the
  `cfg is None` check three lines below, so a missing config crashes here" is a
  finding. Drop anything you cannot state that way.

If the code is clean, say so plainly and list nothing.

**5. Skipped files.** The `skipped.tsv` contents as a short table, with a
sentence noting these were excluded as spec/doc/lockfile/generated/binary and can
be re-admitted with `--include <glob>`. Never omit this section — the developer
must be able to confirm nothing load-bearing was filtered out.

### 5. Report back

Tell the user the report is open, give its path, and summarize in **three lines
at most**: what the branch does, the base it was compared against, and the count
of findings by severity. The report holds the detail; do not reprint it in chat.

## Scope — what this skill does NOT do

It reads. It writes exactly one file, the report, in a tmp directory. It never
edits the code it reviews, never commits, never pushes, never merges, and never
touches `openspec/`. If the review finds something worth fixing, say so and stop
— fixing it is a separate request, and `arbor-auto-work` is where that goes.

Uncommitted working-tree changes are **not** included; the script warns when it
sees them. If the user wants those reviewed instead, that is `/code-review`.
