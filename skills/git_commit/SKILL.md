---
name: git_commit
description: Use when committing staged changes with a Conventional Commit.
---

# Git Commit

## When to Use

Use this skill when:
- The user wants to commit current staged changes
- The user asks for a commit message based on staged diff
- The user wants a Conventional Commit generated from actual code intent

Do not use this skill when:
- Nothing is staged
- The user only wants a review, not a commit
- The user wants to edit the message manually before committing

## Required Workflow

### 1. Verify staged changes exist

Run:

```bash
git diff --cached --name-only
```

If nothing is staged, stop and tell the user to stage files first.

### 2. Inspect the staged content

Run:

```bash
git diff --cached --stat
git diff --cached
```

Read the diff to understand the intent of the change. Do not generate the message from file counts, line counts, or filenames alone.

### 3. Check commit atomicity

Before committing, check whether the staged files belong to one coherent change.

Usually atomic:
- one feature or bug fix in a single area
- source change plus directly related tests
- small docs or config update tied to the same change

Usually not atomic:
- unrelated backend, frontend, and docs changes in one commit
- multiple features bundled together
- refactor mixed with unrelated fixes

If the commit looks non-atomic, stop and tell the user to split it first unless they explicitly want one combined commit.

### 4. Write the commit message

Use Conventional Commit format:

```text
<type>(<scope>): <subject>
```

Scope is optional:

```text
<type>: <subject>
```

Rules:
- English only
- Imperative mood
- Subject max 50 characters
- No trailing period
- Prefer a one-line commit for simple changes
- Add a body only when the change is non-obvious
- Add `!` and `BREAKING CHANGE:` footer only for real breaking changes
- Never add `Co-Authored-By`, AI, or Agent attribution
- Do not write vague summaries like `fix: 9 files`
- Do not describe edits mechanically as `update file`, `modify code`, or `cleanup changes`
- Prefer describing purpose, not implementation noise

### 5. Choose the right type

- `feat`: new user-facing behavior or capability
- `fix`: bug fix or correctness fix
- `docs`: documentation only
- `style`: formatting only, no behavior change
- `refactor`: structural change without behavior change
- `perf`: performance improvement
- `test`: add or adjust tests
- `build`: build tooling or dependencies
- `ci`: CI workflow/config changes
- `chore`: maintenance that does not fit above
- `revert`: reverting an earlier commit

### Conventional Commit Reference

- Breaking change format: `<type>(<scope>)!: <subject>`
- Leave one blank line between subject and body
- Body should explain why the change exists when needed
- For non-obvious changes, explain rationale rather than repeating the diff
- Use `BREAKING CHANGE:` footer only for real compatibility breaks
- Never add AI or agent signature footers

### 6. Commit directly

For a one-line commit:

```bash
git commit -m "<subject>"
```

For a commit with body:

```bash
git commit -m "<subject>" -m "<body>"
```

Do not open an editor. Do not ask interactive yes/no questions unless the user explicitly asked for a preview instead of a commit.

## Message Quality Bar

The message must reflect why the change exists.

Good:

```text
fix(auth): handle missing refresh token
refactor(git_commit): remove interactive helper scripts
docs(git_commit): simplify commit workflow
```

Bad:

```text
fix: 9 files
chore: update code
refactor: modify scripts
```

## Default Behavior

If the user says "commit it" or equivalent:
- inspect staged diff
- check whether the staged change is atomic
- generate the message yourself
- run `git commit`
- report the final message back to the user

If the user asks for message only:
- inspect staged diff
- return the proposed message
- do not run `git commit`
