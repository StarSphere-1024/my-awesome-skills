# Python Domain Constraints & Reconnaissance Rules

This file provides Python-specific constraints. When the inferred domain is Python, you MUST apply these rules and inject the provided `<domain_constraints>` template into your final output.

---

## 1. Pre-Execution Reconnaissance (Mandatory)

Before writing any code or tests, use read-only commands (`cat`, `ls`) to determine the project's ecosystem:

- **Dependency Manager**: Check for `uv.lock`, `pyproject.toml` (Poetry/PDM/Hatch), `Pipfile`, or `requirements.txt`. DO NOT introduce a new package manager; strictly use the existing one.
- **Linting/Formatting**: Check `pyproject.toml` or `.ruff.toml` to see if `Ruff`, `Black`, `Flake8`, or `Mypy` are used. Adhere to the existing config.
- **Project Structure**: Identify if it's a Django app, FastAPI microservice, or standard package (e.g., `src/` layout). Match the existing architecture.

---

## 2. Hard Architectural Constraints

- **Type Hints (PEP 484)**: ABSOLUTELY MANDATORY for all function/method signatures and complex variables.
- **Docstrings**: All public modules, classes, and functions must have Google-style or Sphinx-style docstrings.
- **Testing**: `pytest` is the ONLY acceptable testing framework. Do not use `unittest.TestCase`.

---

## 3. High-Risk Anti-Patterns to Prevent

You must actively prevent the following common Python errors in your generated code:

### 3.1 Mutable Default Arguments

**NEVER use `list`, `dict`, or any mutable object as a default argument.** Use `None` and initialize inside the function.

```python
# ❌ FORBIDDEN: Mutable default argument
def add_item(item: str, items: list = []) -> list:
    items.append(item)
    return items

# Bug: All calls share the same list!
# >>> add_item("a")  # ["a"]
# >>> add_item("b")  # ["a", "b"] - unexpected!

# ✅ CORRECT: Use None sentinel
def add_item(item: str, items: Optional[list] = None) -> list:
    if items is None:
        items = []
    items.append(item)
    return items
```

**Applies to:** `list`, `dict`, `set`, `defaultdict`, any mutable object

### 3.2 Asyncio Blocking

**In `async def` functions, STRICTLY FORBID synchronous blocking I/O calls** (e.g., `requests.get`, `time.sleep`, `open()`). Force the use of async equivalents.

```python
# ❌ FORBIDDEN: Blocking calls in async context
async def fetch_user_data(user_id: int) -> dict:
    response = requests.get(f"https://api.example.com/users/{user_id}")  # BLOCKS!
    time.sleep(1)  # BLOCKS entire event loop!
    return response.json()

# ✅ CORRECT: Async equivalents
import asyncio
import aiohttp

async def fetch_user_data(user_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.example.com/users/{user_id}") as response:
            await asyncio.sleep(1)  # Non-blocking
            return await response.json()
```

**Blocking calls to replace:**

| Synchronous (BLOCKS) | Asynchronous Replacement |
|---------------------|-------------------------|
| `requests.get()/post()` | `aiohttp.ClientSession().get()/post()` |
| `time.sleep(1)` | `await asyncio.sleep(1)` |
| `open()` / `read()` | `aiofiles.open()` / `await read()` |
| `subprocess.run()` | `await asyncio.create_subprocess_exec()` |

### 3.3 Silent Failures

**Forbid `except:` or `except Exception: pass`.** Catch specific exceptions and log them.

```python
# ❌ FORBIDDEN: Bare except
try:
    result = risky_operation()
except:
    pass  # Swallows all exceptions including KeyboardInterrupt

# ❌ FORBIDDEN: Silent failure
try:
    result = risky_operation()
except Exception:
    result = None  # What went wrong?

# ✅ CORRECT: Specific exception with logging
import logging

try:
    result = risky_operation()
except ConnectionError as e:
    logging.error("Connection failed: %s", e)
    raise
except ValueError as e:
    logging.error("Invalid value: %s", e)
    return default_value
```

### 3.4 Circular Imports

**Be mindful of import structures.** Prefer late imports or structural refactoring if circular dependencies arise.

```python
# ❌ FORBIDDEN: Circular import pattern
# module_a.py
from module_b import process_data
def handle_data(data):
    return process_data(data)

# module_b.py
from module_a import handle_data  # Circular! Module b imports module a
def process_data(data):
    return handle_data(data)

# ✅ CORRECT: Restructure to avoid circular dependency
# Move shared functionality to a third module, or use late imports
def process_data(data):
    from module_a import handle_data  # Late import inside function
    return handle_data(data)
```

---

## 4. TDD Mocking Rules

- External I/O (Databases, Redis, HTTP APIs, Filesystem) MUST be isolated in tests.
- Use `unittest.mock` (specifically `patch`, `MagicMock`) or `pytest-mock` to stub these external boundaries.
- Never write a test that makes a real network request without the user's explicit `<clarification_protocol>` approval.

### 4.1 Mock Categories

Mock these categories in tests:
- Database queries
- HTTP requests (external APIs)
- File system operations
- Time-dependent operations (`datetime.now()`)
- Random number generation (for deterministic tests)

```python
from unittest.mock import patch, MagicMock

def test_login_calls_db_with_correct_query():
    with patch("src.auth.Database") as mock_db:
        mock_db.query.return_value = {"id": 1, "user": "test"}

        response = client.post("/login", json={"user": "test", "pass": "secret"})

        mock_db.query.assert_called_once_with(
            "SELECT * FROM users WHERE username = ?",
            ("test",)
        )
```

### 4.2 pytest Test Style

```python
# ✅ GOOD: pytest style
def test_login_returns_token(mock_db):
    response = client.post("/login", json={"user": "test", "pass": "secret"})
    assert response.status_code == 200
    assert "token" in response.json()

# ❌ BAD: unittest style
class TestLogin(unittest.TestCase):
    def test_login_returns_token(self):
        ...
```

---

## 5. Code Standards

### 5.1 PEP8 Compliance

**Mandatory:**
- 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black default)
- Blank lines between functions: 2
- Imports on separate lines, standard library first

### 5.2 Type Hints (Mandatory)

**All function signatures MUST have type hints.**

```python
# ✅ GOOD: Complete type hints
from typing import Optional, List, Dict, Any

def process_user_data(
    user_id: int,
    name: str,
    email: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Process and validate user data."""
    return {"id": user_id, "name": name, "email": email}

# ❌ BAD: No type hints
def process_user_data(user_id, name, email=None, tags=None):
    return {"id": user_id, "name": name, "email": email}
```

### 5.3 Docstrings (Mandatory)

**All public functions and classes MUST have docstrings.**

```python
def calculate_shipping_cost(weight: float, destination: str) -> float:
    """
    Calculate shipping cost based on weight and destination.

    Args:
        weight: Package weight in kilograms
        destination: Destination country code (ISO 3166-1 alpha-2)

    Returns:
        Shipping cost in USD

    Raises:
        ValueError: If weight is negative or destination is invalid
    """
    if weight < 0:
        raise ValueError("Weight cannot be negative")
    return BASE_RATE * weight * get_zone_multiplier(destination)
```

---

## 6. Dependency Management Checklist

**BEFORE writing any code, use `cat` to check the project's dependency management:**

```bash
# Check for dependency files in order of preference
cat pyproject.toml      # Modern: poetry, pdm, hatch
cat requirements.txt    # pip
cat Pipfile             # pipenv
cat setup.py            # Legacy setuptools
cat uv.lock             # uv (new standard)
```

**Determine:**
- [ ] Which package manager is used (uv, poetry, pip, pipenv, pdm)
- [ ] Existing dependencies (avoid adding duplicates)
- [ ] Python version requirement (check `python = "3.x"` or `requires-python`)
- [ ] Test dependencies (pytest already installed?)
- [ ] Linting/formatting tools (black, ruff, mypy config)

**Add dependencies appropriately:**
- `uv add <package>` for uv projects
- `poetry add <package>` for poetry projects
- `pip install <package>` and update `requirements.txt` for pip
- `pipenv install <package>` for pipenv

---

## 7. Injection Template (ACTION REQUIRED)

*Copy the following XML block exactly and inject it into your final Prompt output under the domain constraints section:*

```xml
<domain_constraints>
[PYTHON CORE RULES]
1. ECOSYSTEM: Strictly use the project's existing dependency manager (uv/poetry/pip) and linter (ruff/black/mypy).
2. TDD & MOCKING: Use `pytest`. You MUST use `unittest.mock` to isolate all database and network I/O.
3. TYPING: 100% Type Hints coverage for function signatures is mandatory.
4. ANTI-PATTERNS (FATAL):
   - DO NOT use mutable default arguments (use `None`).
   - DO NOT use synchronous blocking calls (e.g., `requests`, `time.sleep`) inside `async` functions.
   - DO NOT use bare `except` clauses.
</domain_constraints>
```

---

## 8. Common Python Project Structures

**Reconnaissance: Identify project pattern**

```
# Modern FastAPI/Pydantic
src/
  app/
    main.py
    api/
    models/
    services/
  tests/
pyproject.toml

# Django
project/
  manage.py
  app_name/
    models.py
    views.py
    tests.py
  requirements.txt

# Simple package
package_name/
  __init__.py
  module.py
tests/
  test_module.py
setup.py
```

**Use reconnaissance to match existing patterns, not impose new ones.**
