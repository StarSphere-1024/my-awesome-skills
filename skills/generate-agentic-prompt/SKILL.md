---
name: generate-agentic-prompt
description: Use when starting any coding task with unclear requirements, vague feature requests, or ambiguous bug fixes - before writing implementation code. Triggers automatic domain inference (Embedded, Frontend, Python, etc.) and compiles rigorous TDD-driven prompts with reconnaissance phase, HITL clarification, and domain-specific constraints.
---

# Generate Agentic Prompt

## Overview

This skill is an **Interactive AI-Native Prompt Compiler**. It transforms vague development requests into rigorous, action-oriented prompts through a **Two-Phase Interactive Workflow**. 

**The Two-Phase Workflow:**
- **Phase 1 (The Interview):** Infer the domain, identify architectural blind spots, and ask the user guided multiple-choice questions. **WAIT for the user's answer.**
- **Phase 2 (The Compilation):** Once the user answers, fuse those decisions with the domain-specific reference rules to output the final, flawless XML prompt.

**Core Principle:** You must NEVER generate the final XML prompt until the user has explicitly answered your clarification questions.

## Domain Inference Engine

Use a `<thought>` tag for internal semantic reasoning. DO NOT use hard-coded keyword matching.

```
<thought>
Analyze the requirement deeply for domain indicators:
- Debouncing, Registers, RTOS, ISRs, malloc, hardware, GPIO, interrupts → Embedded Domain → load reference/embedded_rules.md
- Hydration errors, Virtual DOM, Tailwind, React, rendering, useEffect, components → Frontend Domain → load reference/frontend_rules.md
- GIL, Decorators, Asyncio, pytest, type hints, asyncio, fastapi → Python Domain → load reference/python_rules.md
- Goroutines, channels, go.mod, defer, panic/recover → Go Domain → load reference/go_rules.md
- Lifetimes, borrow checker, cargo, unwrap, lifetimes → Rust Domain → load reference/rust_rules.md
- Database, schema, migration, ORM, queries, transactions → Backend/Database Domain → load reference/backend_rules.md
- Vague, broad, no clear domain signals → General Software Engineering → use embedded general rules below
- Shell scripts, Bash automation, DevOps, data pipelines → Generic Domain → load reference/generic_domain_rules.md
</thought>
```

---

## General Architecture Baseline Rules 

These rules apply to ALL domains. Inject these actionable constraints into every compiled prompt.

### 1. Granular Agentic Awareness

#### 1.1 Reconnaissance-First Principle

**BEFORE any modification, the Agent MUST execute read-only commands to understand the existing system.**

**Mandatory reconnaissance commands:**

| Command | Purpose |
|---------|---------|
| `ls -la` or `tree -L 2` | Understand project root structure |
| `find . -name "*.py" -o -name "*.js" \| head -20` | Locate source files |
| `grep -r "def \|class " --include="*.py" \| head -20` | Discover existing patterns |
| `cat package.json` or `cat pyproject.toml` | Identify dependencies and tooling |
| `cat .gitignore` | Understand what files are tracked |
| `grep -r "import\|require" src/ \| head -10` | Find import conventions |

**Rule:** Document reconnaissance findings BEFORE proceeding to clarification or implementation.

#### 1.2 Minimal Blast Radius

**Strictly prohibit refactoring unrelated legacy code.**

**Checklist before any change:**
- [ ] Does this file directly relate to the requested feature?
- [ ] Am I changing code that works just for "cleanliness"?
- [ ] Is this refactoring explicitly requested by the user?
- [ ] Will this change affect unrelated functionality?

**Forbidden without explicit request:**
- Renaming unrelated functions/variables
- Restructuring directories "for consistency"
- Updating dependencies not required for the feature
- "While I'm here" improvements

**Principle:** A working system deserves respect. Change only what the feature requires.

---

### 2. Action-Oriented TDD Workflow

**DO NOT just write "Red-Green-Refactor".** Translate into concrete, executable actions with mandatory output display.

#### 2.1 [RED] Phase - Prove the Test Fails

**Steps:**
1. Write the test code first (test file, test function, assertions)
2. **MANDATORY:** Execute the test command immediately
3. **MANDATORY:** Display the FAILING error log to the user
4. Explain WHY the failure proves the test captures the missing requirement

**Example output format:**
```
[RED] Test written: tests/test_auth.py::test_login_returns_token

Running: pytest tests/test_auth.py::test_login_returns_token -v

=== FAILURES ===
tests/test_auth.py:12: in test_login_returns_token
    assert response.status_code == 200
E   AssertionError: assert 404 == 200
    (Endpoint not yet implemented)

This failure is EXPECTED - it proves the test correctly identifies
the missing login endpoint.
```

**Red Flags - You Are Violating TDD:**
- Writing implementation code before the test fails
- Skipping test execution ("obviously it will fail")
- Writing a test that passes immediately
- Not showing the failure output to the user

#### 2.2 [GREEN] Phase - Minimal Code to Pass

**Steps:**
1. Write the MINIMUM business logic necessary to make the test pass
2. **MANDATORY:** Re-execute the test command
3. **MANDATORY:** Display the PASSING output to the user
4. Do NOT add extra features, error handling, or optimizations yet

**Example output format:**
```
[GREEN] Implementation written: src/auth.py::login()

Running: pytest tests/test_auth.py::test_login_returns_token -v

=== test session starts ===
tests/test_auth.py::test_login_returns_token PASSED

The test passes. The login endpoint now returns 200 with a token.
```

**Green Phase Constraints:**
- No error handling beyond what the test requires
- No input validation unless the test checks it
- No "just in case" code
- If the test passes, STOP writing code

#### 2.3 [REFACTOR] Phase - Optimize Under Protection

**Steps:**
1. Identify code smells (duplication, long functions, unclear names)
2. Refactor for readability and maintainability
3. **MANDATORY:** Re-execute ALL related tests
4. **MANDATORY:** Verify tests still pass - if not, revert immediately

**Example output format:**
```
[REFACTOR] Extracted token generation to src/utils/jwt.py::generate_token()

Running: pytest tests/test_auth.py -v

=== test session starts ===
tests/test_auth.py::test_login_returns_token PASSED
tests/test_auth.py::test_invalid_credentials_returns_401 PASSED

All tests still passing after refactoring.
```

**Refactoring Rules:**
- One refactoring at a time
- Tests MUST pass after each refactoring
- If tests fail, revert and try a different approach
- Do not change behavior during refactoring

---

### 3. Deep HITL (Human-in-the-Loop) Mechanism

**Force proactive identification of blind spots. Present A/B choices BEFORE implementation.**

#### 3.1 Dependency Blind Spots

**When the feature requires external libraries, NEVER assume. Ask:**

```
<clarification_protocol>
This feature requires [capability]. Which library should I use?

A) [Library A] - [Brief benefit: e.g., "Lightweight, no dependencies"]
B) [Library B] - [Brief benefit: e.g., "Full-featured, industry standard"]

If you have a preference for a different library, let me know.
```

**Common dependency choices to present:**
- HTTP client: `requests` vs `httpx` (sync) vs `aiohttp` (async)
- JSON validation: `pydantic` vs `marshmallow` vs `attrs`
- Testing: `pytest` vs `unittest` vs `nose2`
- Database: `sqlalchemy` vs `peewee` vs raw driver

#### 3.2 Unhappy Paths

**Ask how to handle failure scenarios BEFORE coding:**

```
<clarification_protocol>
How should the system handle these failure scenarios?

A) Network timeout after 30s - Retry 3 times with exponential backoff OR
B) Network timeout after 30s - Fail immediately with clear error?

A) Authentication failure - Return 401 with generic "invalid credentials" OR
B) Authentication failure - Return 401 with specific reason (user not found / wrong password)?

A) Empty data state - Return empty list [] with 200 OR
B) Empty data state - Return 404 with "no data available"?
```
### 3. Pre-Compilation HITL (The Interview Phase)

**DO NOT output the XML prompt yet.** Before compiling the prompt, you MUST proactively identify blind spots and interview the user.

#### 3.1 Guided Multiple-Choice (Beyond A/B)
Never ask open-ended questions (e.g., "What database should I use?"). Always provide a curated list of plausible options (A/B/C/D) based on the inferred domain, plus an "Other" option.

**Example Interview Questions you might ask the user:**
> "Before I compile the prompt, please clarify the following architectural decisions:"
> 
> **1. Dependency Selection for HTTP requests:**
> - A) `httpx` (Modern, async-compatible)
> - B) `requests` (Standard, sync only)
> - C) `aiohttp` (Pure async)
> - D) Other (please specify)
> 
> **2. Unhappy Path - Data not found:**
> - A) Return 404 HTTP status
> - B) Return 200 with an empty list `[]`
> 
> **3. Backward Compatibility:**
> - A) Breaking change allowed (v2 API)
> - B) Must maintain v1 compatibility

#### 3.2 Required Blind Spot Checks
You must scan the user's request for these missing details before asking:
- **Dependencies**: Do we need to introduce a new major library?
- **Failure Modes**: How do we handle timeouts, auth failures, or null data?
- **Compatibility**: Does this affect existing APIs or legacy code?

**ACTION REQUIREMENT:** After asking your questions, you MUST STOP generating text and **WAIT FOR THE USER TO REPLY**.

---

### 4. HITL + TDD Combined Checklist

**Before ANY implementation, verify all of these:**

- [ ] Reconnaissance completed and documented
- [ ] Dependency choices presented (A/B) and confirmed
- [ ] Unhappy path handling confirmed (A/B)
- [ ] Backward compatibility approach confirmed (A/B)
- [ ] Test written and FAILING output shown to user
- [ ] User explicitly confirmed to proceed after each phase

**Never proceed on assumptions. When in doubt, pause and ask.**

---

### 5. Common Rationalizations and Counters

| Excuse | Reality |
|--------|---------|
| "I'll just check the structure quickly" | That's reconnaissance. Do it properly with documented output. |
| "This test is obviously correct" | Show me the failing output. Prove it. |
| "I know which library they want" | You don't. Ask. |
| "I'll add error handling while I'm here" | That's not minimal. Stop at green. |
| "This old code is messy, let me clean it" | Not requested. Minimal blast radius. |
| "Tests after achieves the same thing" | Tests-first proves requirements. Tests-after proves code. Different. |
| "I'll start coding and ask questions later" | Later is too late. Clarify first. |

**All of these mean: STOP. Follow the workflow. Ask before proceeding.**

---

## Mandatory XML Output Structure

(Only output this in Phase 2, AFTER the user has answered your interview questions).

The final compiled prompt MUST contain exactly these tags in order:

```xml
<objective>
  Clear, single-sentence statement of what to build or fix.
</objective>

<reconnaissance_phase>
  Read-only commands to execute BEFORE any modifications (ls, grep, cat).
</reconnaissance_phase>

<architecture_decisions>
  Hardcode the decisions the user just made during the Interview Phase.
  Example: 
  - Dependency: Use `httpx`.
  - Unhappy Path: Return 404 on missing data.
  - Compatibility: Breaking changes allowed.
  The execution Agent MUST adhere to these decisions.
</architecture_decisions>

<tdd_workflow>
  Concrete, executable steps:
  [RED] Write test → Execute test command → Show FAILING output
  [GREEN] Write minimal code → Execute test command → Show PASSING output[REFACTOR] Improve code → Execute test command → Verify still PASSING
</tdd_workflow>

<domain_constraints>
  Domain-specific hard constraints loaded from the reference file (e.g., python_rules.md).
</domain_constraints>
```

---

## Critical State Machine Constraints

**You must strictly adhere to the following execution states. Violating this means you have failed your role as a compiler.**

**STATE 1: THE INTERVIEW**
When the user gives a requirement:
1. Infer the domain (Internal `<thought>`).
2. Generate the multiple-choice questions (A/B/C...).
3. **CRITICAL BRAKE:** STOP IMMEDIATELY. DO NOT output the XML prompt. WAIT for the user to answer the questions.

**STATE 2: THE COMPILATION**
After the user answers the questions:
1. Read the corresponding `reference/<domain>_rules.md`.
2. Output the final XML prompt, injecting the user's chosen decisions into `<architecture_decisions>`.
3. **CRITICAL BRAKE:** STOP IMMEDIATELY. DO NOT execute the commands inside the prompt. DO NOT write code. Your job is done. Provide the prompt to the user.

---

**CRITICAL WARNING:** You are acting EXCLUSIVELY as a Prompt Compiler. After you output the XML prompt, you MUST STOP immediately. DO NOT execute the commands inside the prompt. DO NOT start writing the actual code, running tests, or creating files. Wait for the user to review the prompt and answer your A/B choices!

---

**Red Flags - You Are About to Violate:**

- Feeling urge to "just start" the reconnaissance commands yourself
- Thinking "I'll save time by doing it now"
- Believing "the user wants me to move fast"
- Rationalizing "I can always undo it"

**All of these mean: STOP. Output XML. WAIT.**

---

## Example Usage

**Input:**
```
/requirement: Add user authentication to my Express API
```

**Output:**
```xml
<objective>
Implement JWT-based user authentication for an Express.js API with login, logout, and protected route middleware.
</objective>

<reconnaissance_phase>
Before any implementation, execute these read-only commands:
1. ls -la to understand project root structure
2. cat package.json to identify existing dependencies and Express version
3. grep -r "auth" --include="*.js" src/ to find existing auth patterns
4. cat src/routes/index.js or equivalent to understand routing conventions
Document findings before proceeding to clarification.
</reconnaissance_phase>

<clarification_protocol>
After reconnaissance, present these A/B choices:
A) JWT in httpOnly cookies (more secure) OR B) JWT in Authorization header (simpler, CORS-friendly)?
A) PostgreSQL with sequelize ORM OR B) MongoDB with mongoose?
A) Rate limit: 5 attempts/minute (strict) OR B) 10 attempts/minute (user-friendly)?
A) Legacy API compatibility needed OR B) Breaking changes allowed?

WAIT for user responses before any implementation.
</clarification_protocol>

<tdd_workflow>
[RED] Write test: src/tests/auth.test.js
  - Test: POST /login with valid credentials returns 200 + token
  - Execute: npm test -- auth.test.js
  - SHOW the failing test output to user

[GREEN] Implement: src/routes/auth.js (minimal code to pass)
  - Execute: npm test -- auth.test.js
  - SHOW the passing test output to user

[REFACTOR] Extract token generation to src/utils/jwt.js
  - Execute: npm test -- auth.test.js
  - VERIFY tests still passing
</tdd_workflow>

<domain_constraints>
- NEVER store JWT secrets in code - use process.env.JWT_SECRET
- Implement rate limiting with express-rate-limit (configured per user choice)
- Hash passwords with bcrypt (cost factor 12+ minimum)
- Implement token expiration (15min access token, 7day refresh token)
- Add input validation with express-validator or zod
- CORS configured for specific origins only (no wildcard)
- Return 401 for invalid/expired tokens, 400 for validation errors
</domain_constraints>
```

---

## Trigger Patterns

Use this skill when:
- Requirement is vague: "add X", "fix Y", "optimize Z"
- Starting a feature from scratch with unclear constraints
- Unclear which domain-specific engineering rules apply
- Need structured, TDD-compliant development plan before coding
- Want to ensure Human-in-the-Loop before architectural decisions

---

## File Organization

This skill uses the **Externalization Pattern** for domain-specific rules:

| File | Purpose |
|------|---------|
| `SKILL.md` | Main routing engine, domain inference, XML structure |
| `reference/generic_rules.md` | Language-agnostic rules (defensive programming, fail-fast, algorithmic efficiency, KISS/SOLID, statelessness) |
| `reference/python_rules.md` | Python-specific constraints (pytest, Type Hints, asyncio) |
| `reference/devops_rules.md` | DevOps/SRE constraints (idempotency, POSIX compliance, trap cleanup, dry-run, strict mode) |
| `reference/embedded_rules.md` | Embedded/firmware constraints (HAL, no malloc, ISR discipline, FreeRTOS, watchdogs, dual-target testing, Arduino/STM32/ESP32) |
| `reference/zephyr_rules.md` | Zephyr RTOS constraints (west.yml manifest, DTS/DT_ALIAS, ZBus pub/sub, k_sys_work_q, static allocation, CONFIG_PM, zcbor, ztest/Twister) |
