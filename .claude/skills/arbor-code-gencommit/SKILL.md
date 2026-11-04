---
name: arbor-code-gencommit
description: Generate a concise git commit message from the current staged/unstaged diff and write it to a tmp file. Use when the user wants to generate a commit message. Accepts an optional ticket number to prefix the message.
metadata:
  type: skill
---

Generate a concise commit message from the current staged/unstaged diff, write it to a unique tmp file, and open it for review.

## Steps

### 1. Parse ticket number (optional)

If the user provided a ticket argument (e.g. `ABC-123`), store it as `TICKET`. Otherwise `TICKET` is empty.

### 2. Gather the diff

Run both commands and combine the output:

```bash
git diff --cached -- . ':(exclude).kiro/'
git diff -- . ':(exclude).kiro/'
```

If both return empty, report "Nothing to commit (kiro-only changes or clean working tree)" and stop.

### 3. Generate the commit message

Format:
```
{TICKET } One concise imperative summary

- Bullet per logical change, as short as possible
- Another bullet
```

Rules:
- Summary line: imperative mood ("Add", not "Added"), ≤72 characters, no period; prefix with `TICKET ` (no colon) if set
- The body scales with the change: a trivial change gets the subject only, with no bullets
- **Otherwise, a blank line between the summary and the bullets, always.** Without it, `git commit -F` treats the message as one unbroken paragraph and folds every bullet into the subject line instead of the commit body.
- Each bullet: imperative mood, one short phrase, no filler words, no periods. When the reason for a change isn't obvious from the diff, give the reason its own bullet
- Omit .kiro and test-related changes from bullets **unless the diff contains only test changes** — in that case include them
- Never prose paragraphs, no "this commit", no redundant bullets
- No AI attribution: no `Co-Authored-By` trailer, no "Generated with" line

Example:
```
ABC-123 Add new connectors for the database

- Configure the database to scaffold automatically
- Define connectors
- Add health monitors
```

### 4. Write and open

Generate a unique filename using `mktemp`, write the message, and open it:

```bash
COMMIT_FILE=$(mktemp /tmp/commit_msg.XXXXXX) && mv "$COMMIT_FILE" "${COMMIT_FILE}.txt" && COMMIT_FILE="${COMMIT_FILE}.txt"
cat > "$COMMIT_FILE" << 'MSG'
<generated message>
MSG
open "$COMMIT_FILE"
```

Tell the user the file is open and they can use it with:
```bash
git commit -F <path shown above>
```
