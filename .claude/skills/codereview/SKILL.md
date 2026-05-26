---
name: codereview
description: Use when the user wants a multi-perspective code review of the current branch diff or a GitHub PR. Accepts an optional PR URL; without one, reviews the diff between HEAD and the remote tracking branch.
---

# review

Run a structured code review from 8 independent perspectives in parallel, then synthesize findings into a prioritized report.

## Steps

### 1. Get the diff and context

**If a PR URL was provided** (e.g. `/review https://github.com/org/repo/pull/123`):

```bash
gh pr view <url> --json title,body,baseRefName,headRefName
gh pr diff <url>
```

**If no argument provided** — diff HEAD against the remote tracking branch:

```bash
git remote get-url origin
git rev-parse --abbrev-ref HEAD          # current branch
git merge-base HEAD origin/main          # or origin/<base>
git diff $(git merge-base HEAD origin/main)..HEAD
git log --oneline $(git merge-base HEAD origin/main)..HEAD
```

If the diff is empty, report "Nothing to review — no changes found" and stop.

Store: `DIFF`, `COMMIT_LOG`, `PR_TITLE` (if PR), `PR_BODY` (if PR), `REPO_ROOT`.

### 2. Dispatch 8 parallel review agents

Use the Agent tool to dispatch all 8 agents simultaneously. Each receives the full diff, commit log, and a focused prompt for its perspective.

**Agent prompt template** (customize per perspective):

> You are a code reviewer focused exclusively on [PERSPECTIVE].
> 
> **Context:**
> - Commits: `<COMMIT_LOG>`
> - PR/Branch intent: `<PR_TITLE or branch name>`
>
> **Diff:**
> ```
> <DIFF>
> ```
>
> **Your task:** Review ONLY from the [PERSPECTIVE] lens. For each finding:
> - Severity: CRITICAL / MAJOR / MINOR / SUGGESTION
> - File + line reference
> - Concise description of the issue
> - Suggested fix (one sentence or short code snippet)
>
> If no issues found for your perspective, say "No findings."
> End with a one-line summary score: [PERSPECTIVE]: X issues (C/M/m/S counts).

**The 8 perspectives:**

| # | Perspective | Focus |
|---|-------------|-------|
| 1 | **Completeness** | Does the change fully accomplish the stated intent? Look for TODOs, stubs, half-implemented branches, missing error paths, unhandled states, and gaps between the PR description and the actual code. |
| 2 | **Redundancy** | Is code duplicated within the diff? Does it re-implement utilities that already exist in the codebase? Could helpers be extracted? Check both within the diff and for patterns in existing files that overlap. |
| 3 | **Security** | OWASP Top 10: injection (SQL, shell, path), XSS, broken auth, secrets in code, insecure deserialization, missing input validation, improper error messages that leak internals, dependency risks. |
| 4 | **Efficiency** | Time/space complexity regressions, N+1 query patterns, unnecessary loops or allocations, missing indexes implied by query patterns, blocking calls where async fits, caching opportunities. |
| 5 | **Convention** | Naming (variables, functions, files), formatting consistency, code structure and organization, inline comments (present where needed, absent where obvious), adherence to apparent project style. |
| 6 | **Correctness** | Logic soundness — off-by-one errors, inverted conditions, missing null/undefined guards, unhandled promise rejections, incorrect type assumptions, race conditions, edge case gaps. |
| 7 | **Testability** | Is changed behavior covered by tests? Are tests meaningful (test behavior not implementation)? Are edge cases and error paths tested? Are there untestable patterns introduced (tight coupling, hidden global state)? |
| 8 | **Maintainability** | Cognitive complexity, long functions, deeply nested conditionals, magic numbers/strings, tight coupling, missing abstractions that would aid future change, unclear naming that hinders understanding. |

### 3. Synthesize and present findings

After all agents complete, produce a structured report:

```
## Code Review: <branch/PR title>

### Summary
| Perspective     | Critical | Major | Minor | Suggestion |
|-----------------|----------|-------|-------|------------|
| Completeness    |          |       |       |            |
| Redundancy      |          |       |       |            |
| Security        |          |       |       |            |
| Efficiency      |          |       |       |            |
| Convention      |          |       |       |            |
| Correctness     |          |       |       |            |
| Testability     |          |       |       |            |
| Maintainability |          |       |       |            |

### Findings (ordered by severity)

#### CRITICAL
<findings>

#### MAJOR
<findings>

#### MINOR & SUGGESTIONS
<findings>

### Verdict
APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
One sentence rationale.
```

Verdict rules:
- **APPROVE** — zero Critical/Major findings
- **REQUEST CHANGES** — any Critical finding, or 3+ Major findings
- **NEEDS DISCUSSION** — 1–2 Major findings with no Critical

Omit empty severity sections. Group findings by file when multiple issues exist in the same file.
