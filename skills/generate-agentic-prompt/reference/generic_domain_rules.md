# Generic Domain Rules (Language-Agnostic)

Inject these constraints into the `<domain_constraints>` tag when the task is language-agnostic, algorithmic, or general software engineering (e.g., "Design a rate-limiter", "Write a regex", "Convert JSON to XML", "Architect a caching layer").

---

## 1. Defensive Programming (防御性编程)

**Always explicitly validate input before processing data.**

### 1.1 Null/Undefined Checks

```
# GOOD: Explicit validation before use
if input is null or input is undefined:
    return error("Input cannot be null")

if collection is empty:
    return default_value

# BAD: Assuming input exists
result = input.value  # May throw null reference exception
```

### 1.2 Boundary Condition Checks

```
# GOOD: Check boundary conditions
if divisor == 0:
    return error("Division by zero")

if index < 0 or index >= array.length:
    return error("Index out of bounds")

if string.length == 0:
    return ""

# BAD: No boundary checks
result = array[index]  # May throw
quotient = numerator / denominator  # May divide by zero
```

### 1.3 Collection Safety

```
# GOOD: Safe collection handling
if items is null or items.length == 0:
    return []

for item in items:
    if item is valid:
        process(item)

# BAD: Unsafe iteration
for item in items:  # May be null
    process(item.value)  # May be null
```

---

## 2. Fail-Fast Principle (快速失败)

**Never swallow errors silently. Report failures immediately.**

### 2.1 Explicit Error Reporting

```
# GOOD: Fail immediately with clear message
if state == INVALID:
    throw new IllegalStateException("Cannot process: state is INVALID")
    # STOP - do not continue

if input.isInvalid():
    return Result.error("Invalid input: " + input.getReason())
    # Do NOT proceed with corrupted data

# BAD: Silent failure or continuation
if input.isInvalid():
    pass  # Continue anyway - data is corrupted

try:
    process()
except:
    pass  # Swallows all errors - debugging impossible
```

### 2.2 Impossible State Detection

```
# GOOD: Assert invariants
if current_balance < 0:
    throw new IllegalStateException("Balance cannot be negative")

if order.status == SHIPPED and order.ship_date is null:
    throw new IllegalStateException("Shipped order must have ship date")

# BAD: Allow impossible states to propagate
# Continue processing negative balance
# Allow shipped orders without dates
```

### 2.3 Error Propagation

```
# GOOD: Propagate errors up the call stack
function parseInput(data):
    if not data.isValidJson():
        return ParseError("Invalid JSON: " + data.getErrorMessage())
    # Caller decides how to handle

# BAD: Swallow errors at wrong level
function parseInput(data):
    try:
        return parse(data)
    except:
        return null  # Caller doesn't know why it failed
```

---

## 3. Algorithmic Efficiency (算法效率)

**Explicitly consider Time and Space complexity for data processing.**

### 3.1 Complexity Analysis Required

```
# GOOD: Document and justify complexity
# Time: O(N log N) - sorting dominates
# Space: O(1) - in-place sort, O(N) auxiliary for merge sort
function sortAndProcess(items):
    items.sort()  # O(N log N)
    return processSorted(items)  # O(N)

# BAD: No complexity consideration
# Using nested loops when hash map would work
# O(N²) when O(N) is possible
for i in items:
    for j in items:  # Unnecessary quadratic complexity
        if i == j:
            ...
```

### 3.2 Avoid Brute Force When Better Exists

```
# GOOD: Use appropriate data structures
# Find duplicates: O(N) with hash set
function findDuplicates(items):
    seen = new Set()
    duplicates = []
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return duplicates

# BAD: Brute force O(N²)
function findDuplicates(items):
    for i from 0 to items.length:
        for j from i+1 to items.length:
            if items[i] == items[j]:  # Quadratic!
                ...
```

### 3.3 Space-Time Tradeoffs

```
# GOOD: Use memoization when computation is expensive
cache = new Map()
function fibonacci(n):
    if n in cache:
        return cache[n]  # O(1) lookup
    if n <= 1:
        return n
    result = fibonacci(n-1) + fibonacci(n-2)
    cache[n] = result
    return result

# BAD: Recompute same values repeatedly
# Time: O(2^N), Space: O(N) stack
function fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)  # Exponential!
```

---

## 4. KISS & SOLID (极简与开闭原则)

**Keep logic simple. Resist over-engineering.**

### 4.1 Single Responsibility Principle (SRP)

```
# GOOD: One function, one responsibility
function validateEmail(email):
    return regex.match(email)

function normalizeEmail(email):
    return email.toLowerCase().trim()

function saveUser(email):
    if not validateEmail(email):
        return error
    normalized = normalizeEmail(email)
    database.save(normalized)

# BAD: Multiple responsibilities in one function
function saveUser(email):
    # Validates, normalizes, connects to DB, saves, sends email, logs
    # Does everything - hard to test, hard to reuse
```

### 4.2 Keep It Simple, Stupid (KISS)

```
# GOOD: Simple, direct logic
function calculateTotal(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return total * (1 + tax_rate)

# BAD: Over-engineered
function calculateTotal(items):
    strategy = PricingStrategyFactory.getStrategy(items)
    calculator = strategy.createCalculator()
    visitor = PricingVisitor()
    calculator.accept(visitor)
    return visitor.getResult().applyTax().applyDiscounts()...
```

### 4.3 Don't Invent Patterns for Simple Tasks

```
# GOOD: Direct data transformation
function convertJsonToXml(json):
    xml = "<root>"
    for key, value in json:
        xml += f"<{key}>{value}</{key}>"
    xml += "</root>"
    return xml

# BAD: Unnecessary abstraction layers
interface IConverter { convert(data): }
class JsonToXmlConverter implements IConverter { ... }
class ConverterFactory { getConverter(type): ... }
class XmlOutputBuilder { build(node): ... }
# For a simple 3-line transformation!
```

---

## 5. Statelessness Preference (无状态优先)

**Design functions as pure functions whenever possible.**

### 5.1 Pure Functions

```
# GOOD: Pure function (output depends only on input)
function add(a, b):
    return a + b

function transform(data, transformation):
    return transformation.apply(data)  # Same input → same output

# No side effects, no global state mutation

# BAD: Impure function with hidden dependencies
counter = 0
function increment():
    counter += 1  # Mutates global state
    return counter  # Same call → different result

function process(items):
    global_cache.update(items)  # Side effect
    logToFile(items)  # Side effect
    return transform(items)
```

### 5.2 No Mutation of Input

```
# GOOD: Return new data, don't mutate
function addItem(items, item):
    return [...items, item]  # New array

function updateProperty(obj, key, value):
    return { ...obj, [key]: value }  # New object

# BAD: Mutate input
function addItem(items, item):
    items.push(item)  # Modifies original
    return items

function updateProperty(obj, key, value):
    obj[key] = value  # Modifies original
    return obj
```

### 5.3 Side Effect Isolation

```
# GOOD: Isolate side effects
# Pure core logic
function calculateOrderTotal(items, tax_rate):
    subtotal = sum(item.price * item.quantity for item in items)
    return subtotal * (1 + tax_rate)

# Side effect layer (separate)
function processOrder(order):
    total = calculateOrderTotal(order.items, order.tax_rate)  # Pure
    database.save(order)  # Side effect
    sendConfirmationEmail(order.customer, total)  # Side effect
    return { success: true, total: total }

# BAD: Side effects mixed with logic
function processOrder(order):
    total = 0
    for item in order.items:
        total += item.price * item.quantity
        logAccess(item)  # Side effect in calculation
    total *= (1 + order.tax_rate)
    database.save(order)
    sendConfirmationEmail(order.customer, total)
    return total
```

---

## 6. Generic Domain Constraints Template

**Inject this into `<domain_constraints>` when compiling language-agnostic prompts:**

```xml
<domain_constraints>
Generic software engineering constraints (language-agnostic):

DEFENSIVE PROGRAMMING:
- Check null/undefined before any property access
- Validate empty collections before iteration
- Check boundary conditions (divide by zero, array bounds)
- Validate input format before processing

FAIL-FAST:
- Throw explicit errors for invalid input - never continue silently
- Detect and report impossible states immediately
- Propagate errors up the call stack with clear messages
- No bare try-catch that swallows all exceptions

ALGORITHMIC EFFICIENCY:
- Explicitly state Time and Space complexity for algorithms
- Avoid O(N²) when O(N log N) or O(N) exists
- Use appropriate data structures (hash maps for lookups, sets for uniqueness)
- Consider memoization for expensive repeated computations

KISS & SOLID:
- One function = one responsibility (SRP)
- Keep logic as simple as possible - resist over-engineering
- Don't invent design patterns for simple data transformations
- Prefer composition over inheritance when it reduces complexity

STATELESSNESS:
- Pure functions preferred: output depends only on input
- Avoid mutation of input data - return new copies
- Isolate side effects (IO, network, database) from business logic
- No hidden global state dependencies
</domain_constraints>
```

---

## 7. Common Rationalizations and Counters

| Excuse | Reality |
|--------|---------|
| "This input is always valid" | It won't be. Validate anyway. |
| "The error will be caught later" | Later is too late. Fail fast. |
| "O(N²) is fine for small N" | N grows. Future you will curse past you. |
| "This pattern makes it more maintainable" | Simple is more maintainable than "clever". |
| "Mutable state is more efficient" | Premature optimization. Correctness first. |
| "I'll add validation after the core logic works" | Validation IS the core logic. Without it, the logic is wrong. |

**All of these mean: STOP. Follow the principles. Write correct code.**

---

## 8. When This Domain Applies

Use generic domain rules when the task is:

- **Algorithm design**: Sorting, searching, graph algorithms, dynamic programming
- **Data transformation**: JSON↔XML, CSV parsing, format conversion
- **Architecture design**: Rate limiters, caches, load balancers, circuit breakers
- **Regex patterns**: Validation, parsing, text extraction
- **Mathematical logic**: Calculations, statistics, numerical methods
- **General engineering**: System design, API design, protocol design

**Do NOT use when:**
- Task is clearly Python, JavaScript, Go, Rust, etc. (use domain-specific rules)
- Task is embedded systems (use embedded rules)
- Task is frontend/React (use frontend rules)
- Task is database/SQL (use backend rules)
