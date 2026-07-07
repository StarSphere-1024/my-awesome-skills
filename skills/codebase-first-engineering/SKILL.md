---
name: codebase-first-engineering
description: Apply system-aware engineering judgment before modifying an existing codebase. Use when making code changes in a repo, especially when requirements are ambiguous, architecture-sensitive, hardware-facing, concurrent, protocol-related, or likely to affect shared behavior.
---

# Codebase First Engineering

## Overview

Use this skill to move from request to change without guessing the shape of the system. The goal is to understand the existing boundaries, identify the dangerous assumptions, make the smallest coherent edit, and verify the result.

## Operating Mode

- Prefer reading the codebase over asking broad questions.
- Ask the user only when an unknown changes the intended behavior, safety, data ownership, or verification path.
- If a reasonable assumption is needed, state it briefly and proceed.
- Do not turn the workflow into a long planning ritual for small, obvious changes.
- Preserve user changes and local conventions; do not clean up unrelated code.

## Workflow

### 1. Pin Down The Outcome

Before editing, clarify enough to answer:

- What user-visible, test-visible, or hardware-visible behavior should change?
- What must remain compatible?
- What is the smallest observable success condition?
- What cannot be verified locally, and how should that be reported?

### 2. Read The System Shape

Inspect the code around the change before designing the change. Look for:

- Entry points and callers.
- Data ownership, lifetimes, and mutation points.
- State transitions and error paths.
- Concurrency, interrupts, DMA, async callbacks, locks, queues, or buffers.
- Protocol formats, public APIs, persistence formats, and compatibility constraints.
- Existing names, helpers, module boundaries, logging style, and tests.

### 3. Find The Risky Assumptions

Actively look for the assumptions most likely to cause regressions:

- Is there exactly one owner, reader, writer, or consumer?
- Can this path run concurrently or re-enter?
- Does the buffer or object outlive all users?
- Can an error leave partial state behind?
- Does the change alter timing, ordering, backpressure, or resource use?
- Does the change affect wire format, file format, ABI, shell commands, or user workflows?

If a risky assumption cannot be resolved from code, surface it explicitly before relying on it.

### 4. Choose The Smallest Coherent Edit

Default to the repo's existing patterns:

- Reuse local helpers and naming conventions.
- Keep ownership boundaries intact.
- Avoid broad refactors unless they are required for the requested behavior.
- Avoid new abstractions until duplication is stable and semantically identical.
- Prefer structured parsers and APIs over ad hoc string handling when available.
- Keep behavior changes local and easy to review.

### 5. Define Verification Before Editing

Decide how the work will be checked before writing code:

- Unit, integration, snapshot, or existing project tests.
- Build, lint, typecheck, or formatting commands.
- Manual shell commands, logs, hardware checks, protocol inspection, or screenshots.
- Focused tests for error paths, ownership, compatibility, and regression risk.

When no automated test exists, run the strongest available local check and report the remaining manual validation.

## Implementation Discipline

- Edit only the files needed for the request.
- Keep comments rare and focused on non-obvious reasons.
- Preserve formatting and style already used nearby.
- Update tests or docs when the behavior, contract, or user workflow changes.
- After editing, re-read the changed area as a reviewer: look for stale assumptions, missed error paths, and confusing names.

## Final Response

Close with the facts that matter:

- What changed.
- What was verified.
- What could not be verified locally, if anything.
- Any follow-up that is genuinely useful for the user's next step.
