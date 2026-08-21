---
name: clarify-requirements
description: Use when the user wants to clarify or scope an ambiguous coding requirement without generating a prompt or starting implementation. Ask focused decision-blocking questions, then summarize the agreed requirement.
metadata:
  category: engineering
  tags: requirements, clarification, scope
---

# Clarify Requirements

Help the user turn an ambiguous engineering request into an agreed requirement. This is a conversation and decision-making workflow, not a prompt compiler and not an implementation workflow.

## Boundaries

Use this skill when the user asks to:
- clarify, refine, discuss, scope, or think through a requirement;
- decide what a feature or fix should do;
- distinguish in-scope work from follow-up work; or
- resolve ambiguity before implementation.

Do not use it when the user explicitly asks to:
- generate, compile, or write an implementation prompt for another agent — use `generate-agentic-prompt`;
- implement, change, fix, or build the feature now — follow the normal engineering workflow;
- stress-test a proposed design — use `grill-me` when the user requests adversarial questioning.

Do not inspect the repository, load domain references, prescribe TDD, generate an implementation prompt, or edit code unless the user explicitly changes the requested deliverable. Product intent comes before implementation mechanics.

## Workflow

### 1. Extract the current requirement

Identify, without exposing chain-of-thought:
- the user goal and intended beneficiary;
- stated constraints;
- implied but uncertain behavior;
- decisions that would materially change scope, behavior, compatibility, risk, or acceptance.

Do not ask about details that have a safe, conventional, reversible default. State such a default only when it helps the user decide.

### 2. Ask the minimum high-value questions

Ask only questions needed to make the requirement actionable. Prefer two to five questions per turn. Group related decisions. Use concise multiple-choice options when they make tradeoffs clearer; allow an explicit alternative.

When an interactive `ASK` or equivalent user-question tool is available, use it for these questions. It records each choice structurally and makes the decision loop less error-prone. Present the question, options, consequences, and an `Other` choice through that tool. Use chat only when no such tool is available or a free-form answer is genuinely necessary.

Prioritize questions in this order:
1. Desired outcome and acceptance criteria.
2. Scope and non-goals.
3. Existing behavior and compatibility.
4. User-visible failure or edge-case behavior.
5. Irreversible, costly, security-sensitive, or cross-team decisions.

Avoid questions whose answers can be discovered later from the codebase. Avoid implementation choices such as libraries, internal architecture, test framework, or file names unless the user explicitly asks to decide them now.

For chat fallback, use this format:

```markdown
To make the requirement actionable, please decide:

1. **[Decision]**
   - A. ... — [consequence]
   - B. ... — [consequence]
   - C. Other: ...

2. **[Decision]**
   - A. ...
   - B. ...
```

After asking questions, stop and wait for the user response.

### 3. Maintain a decision ledger

After each answer, update only the relevant parts of this ledger:

```markdown
## Requirement

**Goal:** ...

**In scope:**
- ...

**Out of scope:**
- ...

**Decisions:**
- ...

**Open questions:**
- ...

**Acceptance criteria:**
- ...
```

Do not invent decisions. Mark unsupported assumptions as `[ASSUMPTION]` and ask for confirmation when they can change the result.

### 4. Close the clarification loop

When no decision-blocking uncertainty remains, output the completed ledger and use the available `ASK` or equivalent user-question tool for exactly one next-step question:

- A. Implement it now.
- B. Turn it into an implementation prompt for another agent.
- C. Revise the clarified requirement.

If no interactive question tool is available, ask the same choices in chat. Stop after the question. Do not begin implementation or generate a prompt without an explicit choice.

## Question Quality

A good question changes the implementation contract. A bad question merely transfers routine engineering work to the user.

Ask about examples when behavior is hard to describe. For example, request one expected input/output pair rather than asking broad questions about parsing rules.

If the user has already chosen a direction, preserve it. Surface a risk only when it can materially affect their goal, then offer the smallest meaningful choice set.

## Example

User request:

```text
Add notifications when an invoice is overdue.
```

First response:

```markdown
To make the requirement actionable, please decide:

1. **Recipients**
   - A. Notify only the account owner.
   - B. Notify the account owner and billing contacts.
   - C. Other: ...

2. **Overdue threshold**
   - A. Send once when the due date passes.
   - B. Send at the due date, then repeat on a defined schedule.
   - C. Other: ...

3. **Delivery failure**
   - A. Record the failure and retry automatically.
   - B. Record the failure without retrying.
   - C. Other: ...

4. **Scope**
   - A. Email only.
   - B. Email and in-app notifications.
   - C. Other: ...
```

After the user answers, update the decision ledger. Ask another focused set only if a remaining answer changes the feature contract.