---
name: gencommit
description: Use when the user wants to generate a git commit message from the current diff. Accepts an optional ticket number to prefix the message.
---

# gencommit

Generate a concise commit message from the current staged/unstaged diff, write it to a unique tmp file, and open it for review.

## Steps

### 1. Parse ticket number (optional)

If the user provided an argument (e.g. `/gencommit ABC-123`), store it as `TICKET`. Otherwise `TICKET` is empty.

### 2. Gather the diff

Run both commands and combine the output:

```bash
git diff --cached -- . ':(exclude)openspec/' ':(exclude).kiro/'
git diff -- . ':(exclude)openspec/' ':(exclude).kiro/'
```

If both return empty, report "Nothing to commit (openspec/kiro-only changes or clean working tree)" and stop.

### 3. Generate the commit message

Format:
```
{TICKET: }One concise summary sentence
- Bullet per logical change, as short as possible
- Another bullet
```

Rules:
- Summary line: past tense, ≤72 characters, no period; prefix with `TICKET ` (no colon) if set
- Each bullet: past tense, one short phrase, no filler words, no periods
- Omit openspec, .kiro, and test-related changes from bullets **unless the diff contains only test changes** — in that case include them
- No prose body, no "this commit", no redundant bullets

Example:
```
ABC-123 Added new connectors for the database
- Configured the database to scaffold automatically
- Defined connectors
- Added health monitors
```

### 4. Write and open

Generate a unique filename using `mktemp`, write the message, and open it:

```bash
COMMIT_FILE=$(mktemp /tmp/commit_msg.XXXXXX)
cat > "$COMMIT_FILE" << 'MSG'
<generated message>
MSG
open "$COMMIT_FILE"
```

Tell the user the file is open and they can use it with:
```bash
git commit -F <path shown above>
```
