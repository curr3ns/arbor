---
name: arbor-code-commit
description: Commit the current staged/unstaged diff with a concise generated message, using the same optional ticket/feature prefix convention as arbor-code-gencommit. Use when the user wants changes actually committed, not just a draft message to review.
metadata:
  type: skill
---

Commit the current diff directly: same message format and optional ticket
prefix as arbor-code-gencommit, but this skill stages and runs `git commit`
instead of stopping at a draft file for review.

## Steps

### 1. Parse ticket/feature prefix (optional)

If the user provided a ticket or feature argument (e.g. `ABC-123`), store it
as `TICKET`. Otherwise `TICKET` is empty.

### 2. Decide what to stage

Run `git diff --cached --stat` to see if anything is already staged.

- **Something is already staged:** commit only that. Don't add more — partial
  staging is deliberate curation, not an oversight.
- **Nothing is staged:** run `git status` and review the unstaged/untracked
  file list. Flag anything that looks like it could hold secrets (`.env`,
  `credentials.json`, key/PEM files, etc.) to the user before staging it —
  never stage those silently. Stage the rest with `git add -A`.

If there's nothing staged, unstaged, or untracked, report "Nothing to
commit" and stop.

### 3. Gather the diff

Run both commands and combine the output:

```bash
git diff --cached -- . ':(exclude)openspec/' ':(exclude).kiro/'
git diff -- . ':(exclude)openspec/' ':(exclude).kiro/'
```

If this combined diff is empty but step 2 staged real changes, those changes
are openspec/.kiro-only — skip to step 4 with a plain factual summary (e.g.
`{TICKET } Updated openspec change tracking`) instead of stopping; there is
still something real to commit even though it's excluded from the bullets.

### 4. Generate the commit message

Format:
```
{TICKET } One concise summary sentence
- Bullet per logical change, as short as possible
- Another bullet
```

Rules (same convention as arbor-code-gencommit):
- Summary line: past tense, ≤72 characters, no period; prefix with `TICKET `
  (no colon) if set
- Each bullet: past tense, one short phrase, no filler words, no periods
- Omit openspec, .kiro, and test-related changes from bullets **unless the
  diff contains only test changes** — in that case include them
- No prose body, no "this commit", no redundant bullets

Example:
```
ABC-123 Added new connectors for the database
- Configured the database to scaffold automatically
- Defined connectors
- Added health monitors
```

### 5. Commit

Write the message to a unique tmp file, then commit with it directly:

```bash
COMMIT_FILE=$(mktemp /tmp/commit_msg.XXXXXX) && mv "$COMMIT_FILE" "${COMMIT_FILE}.txt" && COMMIT_FILE="${COMMIT_FILE}.txt"
cat > "$COMMIT_FILE" << 'MSG'
<generated message>
MSG
git commit -F "$COMMIT_FILE"
```

### 6. Confirm

Run `git status` to confirm a clean tree and show the user the new commit
(`git log -1 --oneline`).

## Guardrails

- Never `git push` as part of this skill — commit only, unless the user
  explicitly also asked for a push.
- Never skip hooks (`--no-verify`) or bypass signing. If a pre-commit hook
  fails, fix the underlying issue and re-stage, then commit again — don't
  route around it.
- If a hook or amend would be needed to fix a mistake, create a new commit
  rather than amending, unless the user explicitly asks for an amend.
