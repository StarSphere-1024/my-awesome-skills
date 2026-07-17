---
name: generate-agentic-prompt
description: Use only when the user explicitly asks for a reusable implementation prompt. Interview first, then compile the prompt. For ambiguous requirements without that request, use clarify-requirements.
---

# Generate Agentic Prompt

## Overview

This skill is an interactive prompt compiler. Use it only when the requested deliverable is a reusable implementation prompt, not merely a clearer requirement.

**Phase 1: Interview**
- Infer the domain from semantic signals, not hard-coded keyword matching.
- Identify architectural blind spots.
- Ask guided multiple-choice questions.
- Stop immediately and wait for the user's answer.

**Phase 2: Compilation**
- After the user answers, load the matching domain reference.
- Compile the final implementation prompt in Markdown.
- Stop immediately after outputting the prompt. Do not execute the prompt.

If the user has not explicitly requested an implementation prompt, do not enter this workflow. Use `clarify-requirements` to clarify the requirement first. Never compile the final prompt until the user has explicitly answered the clarification questions.

## Domain Inference

Analyze the requirement internally for domain indicators. Do not expose hidden reasoning.

| Signals | Domain | Reference |
|---|---|---|
| Zephyr, west, DTS, Kconfig, zbus, ztest, Twister | Zephyr RTOS | `reference/zephyr_rules.md` |
| Debouncing, registers, RTOS, ISR, malloc, GPIO, FreeRTOS, Arduino, STM32, ESP32 | Embedded | `reference/embedded_rules.md` |
| GIL, decorators, asyncio, pytest, type hints, FastAPI, Django | Python | `reference/python_rules.md` |
| Shell scripts, Bash automation, deployment, CI, DevOps, SRE, data pipelines | DevOps/SRE | `reference/devops_rules.md` |
| Vague, broad, algorithmic, language-agnostic, no clear domain signals | Generic software engineering | `reference/generic_rules.md` |

If multiple domains apply, load the most specific reference first. For example, Zephyr wins over generic embedded.

## Baseline Rules

These rules apply to every compiled prompt.

### Reconnaissance First

Before any modification, the implementation agent must execute read-only commands to understand the existing system and document findings.

Suggested reconnaissance commands:

| Command | Purpose |
|---|---|
| `ls -la` or `tree -L 2` | Understand project root structure |
| `find . -name "*.py" -o -name "*.js" \| head -20` | Locate source files |
| `grep -r "def \|class " --include="*.py" \| head -20` | Discover existing patterns |
| `cat package.json` or `cat pyproject.toml` | Identify dependencies and tooling |
| `cat .gitignore` | Understand what files are tracked |
| `grep -r "import\|require" src/ \| head -10` | Find import conventions |

The compiled prompt must require reconnaissance findings before implementation.

### Minimal Blast Radius

The compiled prompt must prohibit unrelated refactors.

Checklist to include:
- Does this file directly relate to the requested feature?
- Am I changing working code just for cleanliness?
- Was this refactor explicitly requested?
- Can this affect unrelated behavior?

Forbidden without explicit request:
- Renaming unrelated functions or variables
- Restructuring directories for consistency
- Updating dependencies not required for the feature
- "While I'm here" improvements

### Action-Oriented TDD

Do not merely say "Red-Green-Refactor." Compile concrete actions with mandatory output display.

**RED**
1. Write the test first.
2. Run the specific test command immediately.
3. Show the failing output.
4. Explain why the failure proves the missing requirement is captured.

**GREEN**
1. Write the minimum code needed to pass.
2. Re-run the same test command.
3. Show the passing output.
4. Stop adding behavior once the test passes.

**REFACTOR**
1. Improve readability only under passing tests.
2. Re-run all related tests after each refactor.
3. Revert immediately if tests fail.

### Human-in-the-Loop

Before compiling the final prompt, proactively identify blind spots and ask guided multiple-choice questions. Avoid open-ended questions when a curated choice set is possible.

Blind spots to check:
- Dependencies: Does this require a new major library?
- Failure modes: How should timeouts, auth failures, null data, empty data, or partial failures behave?
- Compatibility: Does this affect existing APIs, data contracts, or legacy behavior?
- Scope: Which files, platforms, or workflows are in or out?

Question format:

```markdown
Before I compile the implementation prompt, please clarify:

1. Dependency selection for HTTP requests:
   - A. `httpx` - modern, async-compatible
   - B. `requests` - standard synchronous client
   - C. `aiohttp` - pure async client
   - D. Other

2. Data-not-found behavior:
   - A. Return 404
   - B. Return 200 with an empty list

3. Backward compatibility:
   - A. Breaking change allowed
   - B. Must preserve v1 behavior
```

After asking the questions, stop and wait for the user to reply.

### Domain Constraint Selection

Treat domain references as candidate pools, not templates to copy.

Only include constraints that directly affect this task's implementation, testing, safety, or likely failure modes. Omit generic best practices unless violating them could plausibly break this specific change.

Selection rules:
- Prefer 3-7 high-signal bullets.
- Include a constraint only if it is relevant to the request, discovered stack, or user's interview answers.
- Merge overlapping constraints into one bullet.
- Do not include platform, framework, library, or subsystem rules for technologies not present in the request or repo.
- Do not copy a full reference section into the final prompt.
- If no extra domain rule is needed, write: `No additional domain-specific constraints beyond the baseline workflow.`

Before writing `# Domain Constraints`, silently apply this relevance test:

```text
Would an implementation agent make a likely task-specific mistake if this constraint were omitted?
```

If the answer is no, omit the constraint.

## Final Markdown Output Structure

Only output this in Phase 2, after the user has answered the interview questions.

The final compiled prompt must use these Markdown sections in order:

```markdown
# Objective

Clear, single-sentence statement of what to build or fix.

# Reconnaissance Phase

Read-only commands to execute before any modifications, plus a requirement to document findings.

# Architecture Decisions

The decisions the user made during the interview.

- Dependency: Use `...`.
- Failure handling: ...
- Compatibility: ...

The implementation agent must follow these decisions.

# TDD Workflow

## RED
- Write ...
- Run ...
- Show ...
- Explain ...

## GREEN
- Implement ...
- Run ...
- Show ...

## REFACTOR
- Refactor ...
- Run ...
- Verify ...

# Domain Constraints

Only the task-relevant constraints selected from the domain reference.
Prefer 3-7 bullets. Do not copy the full reference.
```

## State Machine

### State 1: Interview

When the user explicitly requests an implementation prompt:
1. Infer the domain internally.
2. Generate multiple-choice clarification questions.
3. Stop immediately. Do not output the final prompt. Wait for the user to answer.

### State 2: Compilation

After the user answers:
1. Read the corresponding `reference/{domain}_rules.md`.
2. Select only constraints that pass the relevance test.
3. Output the final Markdown prompt using the required section order.
4. Stop immediately. Do not run commands, write code, or create files.

## Red Flags

If you feel an urge to do any of these, stop and return to the state machine:
- Start reconnaissance yourself
- Save time by coding immediately
- Assume the user wants the fastest default library
- Execute the compiled prompt
- Add implementation after producing the prompt

## Example

Input:

```text
/requirement: Add user authentication to my Express API
```

Phase 1 output:

```markdown
Before I compile the implementation prompt, please clarify:

1. Token storage:
   - A. JWT in httpOnly cookies - safer against token theft
   - B. JWT in Authorization header - simpler for API clients
   - C. Other

2. Persistence layer:
   - A. Use the existing database/ORM discovered during reconnaissance
   - B. Add a new persistence dependency
   - C. Other

3. Rate limit:
   - A. 5 attempts per minute
   - B. 10 attempts per minute
   - C. No rate limit for this change

4. Compatibility:
   - A. Preserve existing API behavior
   - B. Breaking changes allowed
```

Phase 2 output:

```markdown
# Objective

Implement JWT-based user authentication for an Express.js API with login, logout, and protected route middleware.

# Reconnaissance Phase

Before any implementation, execute read-only commands:
1. `ls -la`
2. `cat package.json`
3. `grep -r "auth" --include="*.js" src/`
4. `cat src/routes/index.js` or the equivalent route entrypoint

Document the project structure, dependency manager, route conventions, and existing auth-related code before editing.

# Architecture Decisions

- Token storage: JWT in httpOnly cookies.
- Persistence: Use the existing database/ORM discovered during reconnaissance.
- Rate limit: 5 attempts per minute.
- Compatibility: Preserve existing API behavior.

# TDD Workflow

## RED
- Write `src/tests/auth.test.js`.
- Test `POST /login` with valid credentials returns 200 and a token.
- Run `npm test -- auth.test.js`.
- Show the failing output and explain why the failure captures the missing endpoint.

## GREEN
- Implement the smallest auth route and middleware needed to pass.
- Run `npm test -- auth.test.js`.
- Show the passing output.

## REFACTOR
- Extract token generation only if duplication appears.
- Run `npm test -- auth.test.js`.
- Verify all related tests still pass.

# Domain Constraints

- Do not store JWT secrets in code; use environment configuration.
- Hash passwords with a proven password hashing library.
- Return 401 for invalid or expired tokens.
- Add input validation for auth payloads.
- Configure CORS for explicit origins only.
```

## Trigger Patterns

Use this skill only when the user explicitly requests a reusable implementation prompt, for example:
- “Generate an implementation prompt for another agent.”
- “Turn this requirement into a prompt for Codex or Claude.”
- “Compile a rigorous task prompt before coding.”
- An explicit `/requirement` command whose documented output is an implementation prompt.

Do not use this skill merely because requirements are vague, constraints are unclear, or architectural decisions need confirmation. In those cases, use `clarify-requirements` until the user requests an implementation prompt or direct implementation.

## File Organization

This skill uses external references for domain-specific constraints:

| File | Purpose |
|---|---|
| `SKILL.md` | Main routing engine, domain inference, Markdown output structure |
| `reference/generic_rules.md` | Language-agnostic rules |
| `reference/python_rules.md` | Python-specific constraints |
| `reference/devops_rules.md` | DevOps/SRE constraints |
| `reference/embedded_rules.md` | Embedded/firmware constraints |
| `reference/zephyr_rules.md` | Zephyr RTOS constraints |
