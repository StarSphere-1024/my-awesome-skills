---
name: git_commit
description: Analyzes staged changes, enforces atomic commit discipline, and generates Conventional Commit messages using LLM-driven intent analysis. Use when committing code changes to ensure clean, meaningful git history.
---

# Git Commit Tool

## Overview

Professional Git commit tool that ensures atomic commits with high-quality Conventional Commit messages. Uses LLM to understand the *purpose* of changes rather than just describing file modifications.

## Commands

### Basic Usage

```bash
# Run the commit tool
python ~/.claude/skills/git_commit/git_commit/scripts/git_commit.py
```

### Individual Scripts

```bash
# Check staged changes only
python ~/.claude/skills/git_commit/git_commit/scripts/check_staged_changes.py

# Analyze atomicity of files
python ~/.claude/skills/git_commit/git_commit/scripts/analyze_atomicity.py file1.py file2.py

# Generate commit message from diff (preview only)
python ~/.claude/skills/git_commit/git_commit/scripts/generate_commit_message.py
```

## Step-by-Step Workflow

### Step 1: Stage Changes

```bash
git add <files>
```

### Step 2: Run Commit Tool

```bash
python ~/.claude/skills/git_commit/git_commit/scripts/git_commit.py
```

The tool will:

1. **Check staged changes** - Aborts if nothing staged
2. **Analyze atomicity** - Warns if 3+ domains modified
3. **Generate message** - Uses LLM to create Conventional Commit
4. **Present for approval** - Shows preview before committing
5. **Execute commit** - Runs `git commit -m "<message>"`

### Step 3: Review and Approve

The tool presents the generated message:

```
Commit message preview:
----------------------------------------
feat(auth): add JWT token refresh endpoint

Implement token refresh to extend user sessions
without requiring re-authentication. Uses same
signing algorithm as access tokens.

BREAKING CHANGE: refresh token format changed
----------------------------------------

Proceed with commit? (y/N):
```

Type `y` to commit, or edit the message as needed.

## Commit Message Standards

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Rules

| Rule | Requirement |
|------|-------------|
| Subject mood | Imperative: "fix" not "fixed" |
| Subject length | Max 50 characters |
| Subject ending | No period |
| Body wrapping | 72 characters |
| Language | English only |
| Co-author | FORBIDDEN |
| Breaking change | Add `!` after type, include `BREAKING CHANGE:` footer |

### Types

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting (no logic)
- `refactor` - Restructuring
- `perf` - Performance
- `test` - Tests
- `build` - Build/deps
- `ci` - CI config
- `chore` - Maintenance
- `revert` - Revert commit

### Examples

**Good:**
```
fix(api): handle null user response

Add null check before accessing user properties
to prevent crash on deleted accounts.

Fixes GH-1234
```

**Bad:**
```
Fixed the api thing

Modified file X and file Y to add the null check.
Also updated some other stuff.
```

## Atomic Commit Guidelines

The tool analyzes file paths to detect non-atomic commits:

**Atomic (OK):**
- `src/auth/login.py`, `src/auth/logout.py` (same domain)
- `tests/test_auth.py`, `src/auth/` (code + tests)

**Non-Atomic (Warn):**
- `database/models.py`, `frontend/button.tsx`, `docs/readme.md`
- 3+ unrelated domains modified

When warned, consider splitting:

```bash
# Instead of one big commit:
git add database/ frontend/ docs/
git commit -m "feat: everything"

# Do separate commits:
git add database/
git commit -m "feat(db): add user model"

git add frontend/
git commit -m "feat(ui): add login button"

git add docs/
git commit -m "docs: update readme"
```

## Domain Detection

The tool recognizes these domains:

| Domain | Patterns |
|--------|----------|
| database | `database/`, `db/`, `migrations/`, `models/` |
| backend | `src/`, `api/`, `backend/`, `server/` |
| frontend | `frontend/`, `ui/`, `components/`, `pages/` |
| docs | `docs/`, `documentation/`, `README`, `*.md` |
| config | `config/`, `settings/`, `.github/`, `.gitignore` |
| tests | `tests/`, `test/`, `specs/`, `__tests__/` |
| scripts | `scripts/`, `bin/`, `tools/` |

## LLM Integration

The tool uses this prompt to generate commit messages:

```
You are a Principal Engineer reviewing staged changes.
Your goal is to write a commit message that makes the project's history clean and meaningful.

Focus on the PURPOSE of the change:
- Why was this refactoring done?
- What bug did this logic fix?
- What feature does this enable?

Avoid:
- Redundant phrases like "Modified file X"
- Describing line-by-line changes
- Vague statements like "Updated code"
```

Automatic LLM generation requires the `anthropic` package:

```bash
pip install anthropic
```

If unavailable, the tool falls back to manual message entry.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No changes staged" | Run `git add <files>` first |
| "Non-atomic commit" | Split into smaller commits by domain |
| Subject validation fails | Fix length, mood, or period issues |
| Commit message rejected | Edit and re-submit when prompted |
| LLM not available | Tool falls back to manual entry |

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Atomic Commits](https://www.freshconsulting.com/insights/blog/the-power-of-atomic-commits/)
- [Git Commit Best Practices](https://cbea.ms/git-commit/)
- See `references/conventional_commits.md` for detailed format rules
