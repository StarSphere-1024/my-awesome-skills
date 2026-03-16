#!/usr/bin/env python3
"""Generate structured Python development prompts from vague requirements.

This script transforms vague Python requirements into structured, TDD-driven
prompts that force Agent to clarify before coding.

Usage:
    python generate_prompt.py "add user authentication to the API"
"""

import sys
from typing import Literal


def classify_requirement(requirement: str) -> Literal["bug_fix", "new_feature", "refactor", "performance"]:
    """Classify the requirement type based on keywords."""
    req_lower = requirement.lower()

    if any(word in req_lower for word in ["fix", "broken", "error", "crash", "bug"]):
        return "bug_fix"
    elif any(word in req_lower for word in ["clean", "improve", "restructure", "refactor"]):
        return "refactor"
    elif any(word in req_lower for word in ["slow", "optimize", "speed", "performance"]):
        return "performance"
    else:
        return "new_feature"


def generate_clarification_protocol(requirement: str, req_type: str) -> str:
    """Generate clarification questions with A/B options."""
    questions = []

    # Environment question
    questions.append("""1. **Environment**:
   - A) Use existing virtual environment (venv)
   - B) Create new poetry/uv environment
   Which do you prefer, or is there an existing setup I should use?""")

    # Concurrency question
    questions.append("""2. **Concurrency Model**:
   - A) Synchronous design (blocking I/O, simpler, easier to test)
   - B) Asynchronous design (asyncio, non-blocking, better for high concurrency)
   Which approach fits your use case?""")

    # Dependencies question
    questions.append("""3. **Dependencies**:
   - A) Standard library only (no external dependencies)
   - B) Third-party libraries allowed (pytest, httpx, etc.)
   Are there any libraries I should avoid or prefer?""")

    # Data structures question
    questions.append("""4. **Data Structures**:
   - A) Plain dicts (simple, no dependencies)
   - B) Dataclasses or Pydantic models (type safety, validation)
   Which style matches your existing codebase?""")

    # Testing question
    questions.append("""5. **Testing Approach**:
   - A) Pure unit tests with mocks (fast, deterministic)
   - B) Integration-style tests with real I/O (slower, more realistic)
   Should I mock external boundaries (database, API, filesystem)?""")

    return "\n\n".join(questions)


def generate_tdd_workflow(req_type: str) -> str:
    """Generate TDD workflow instructions."""
    return """**Phase 1 - RED (Failing Test):**
1. Create test file: tests/test_<feature>.py
2. Write pytest test that fails because feature doesn't exist
3. Run: pytest tests/test_<feature>.py -v (expect: FAILED)
4. Show user the RED result explicitly

**Phase 2 - GREEN (Minimal Code):**
1. Write minimum code in <feature>.py to pass the test
2. Include type hints on ALL functions (e.g., `def foo(x: int) -> str:`)
3. Include docstrings on ALL public functions/classes
4. Run: pytest tests/test_<feature>.py -v (expect: PASSED)
5. Show user the GREEN result explicitly

**Phase 3 - REFACTOR:**
1. Improve code structure (extract functions, reduce duplication)
2. Add edge case tests, then handle edge cases
3. Run linters: `ruff check --fix . && ruff format .`
4. Run type checker: `mypy .` (must pass with zero errors)
5. Show user the final cleaned-up result"""


def generate_python_constraints(req_type: str) -> str:
    """Generate Python-specific constraints."""
    constraints = """**Mandatory requirements:**
- Type hints: All functions must have complete type annotations (PEP 484)
- Docstrings: Google-style or NumPy-style on all public functions/classes
- PEP 8: Use ruff for linting and formatting
- Testing: Use pytest (NOT unittest.TestCase classes)
- Mocking: Use unittest.mock or pytest-mock for I/O boundaries
- Environment: Confirm virtual environment before `pip install` or `pytest`"""

    # Add security constraints for certain requirement types
    if any(word in req_type.lower() for word in ["auth", "login", "user", "api"]):
        constraints += """

**Security-specific constraints:**
- NEVER store plaintext passwords (use bcrypt/argon2)
- NEVER log sensitive data (tokens, passwords, API keys)
- ALWAYS use constant-time comparison for secrets
- ALWAYS validate input and sanitize output"""

    constraints += """

**Python-specific traps to avoid:**
- NEVER use mutable default arguments (`list`, `dict`) without `None` guard
- NEVER mix blocking I/O (`requests`, `time.sleep`) in async functions
- NEVER make real I/O calls in unit tests (always mock at boundaries)
- NEVER import circularly (restructure if circular import error occurs)

**Agentic boundaries:**
- Read files before writing: use `ls`, `grep`, `rg` to understand existing patterns
- Minimal changes: modify only files directly affected by this feature
- No scaffolding: don't create unused files or excessive boilerplate"""

    return constraints


def generate_verification(req_type: str) -> str:
    """Generate verification checklist."""
    return """**Before claiming completion, verify:**
1. All tests pass: `pytest -v` (zero failures)
2. Type checking passes: `mypy .` (zero errors)
3. Linting passes: `ruff check .` (zero warnings)
4. Coverage (optional): `pytest --cov=<feature> --cov-report=term-missing`
5. No circular imports in the codebase
6. No blocking calls in async code (if applicable)"""


def build_xml_prompt(requirement: str) -> str:
    """Build the complete XML-structured prompt."""
    req_type = classify_requirement(requirement)
    clarification = generate_clarification_protocol(requirement, req_type)
    tdd_workflow = generate_tdd_workflow(req_type)
    constraints = generate_python_constraints(req_type)
    verification = generate_verification(req_type)

    # Generate context based on requirement type
    context_templates = {
        "bug_fix": "This bug fix ensures the existing functionality works correctly and prevents regression through new tests.",
        "new_feature": "This new feature extends the existing codebase and should integrate cleanly with surrounding modules.",
        "refactor": "This refactoring improves code quality while preserving all existing behavior and test coverage.",
        "performance": "This performance optimization should be measured with benchmarks before and after changes."
    }

    return f"""<objective>
{requirement}
</objective>

<context>
{context_templates[req_type]}
Before starting, use read-only commands (ls, grep, rg, glob) to understand the existing project structure, coding patterns, and test conventions.
</context>

<clarification_protocol>
Before implementing, answer these questions by presenting A/B options to the user:

{clarification}

**WAIT for explicit user response** before proceeding to the TDD workflow. Do not assume - present the options and wait.
</clarification_protocol>

<tdd_workflow>
{tdd_workflow}
</tdd_workflow>

<python_constraints>
{constraints}
</python_constraints>

<verification>
{verification}
</verification>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_prompt.py <python_requirement>")
        print("Example: python generate_prompt.py 'add user login endpoint'")
        sys.exit(1)

    requirement = " ".join(sys.argv[1:])
    prompt = build_xml_prompt(requirement)
    print(prompt)


if __name__ == "__main__":
    main()
