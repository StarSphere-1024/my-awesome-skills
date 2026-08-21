---
name: zephyr-testing
description: Use when adding, reviewing, running, or debugging tests for Zephyr RTOS projects, including Ztest, Twister, testcase.yaml, native_sim, QEMU, pytest harness, shell harness, hardware-in-the-loop testing, regression tests, and coverage reports.
metadata:
  category: embedded
  tags: zephyr, ztest, twister, pytest, qemu
---

# Zephyr Testing Skill

## Step 0 — Detect Environment

Before any test work, gather the project context. Run these commands; adapt to what exists.

```bash
pwd
git status --short
west topdir 2>/dev/null
west config zephyr.base 2>/dev/null
echo "$ZEPHYR_BASE"
echo "$BOARD"
find . -maxdepth 3 \( -name testcase.yaml -o -name sample.yaml \) 2>/dev/null
```

Determine:

- **Project type**: Zephyr main tree, west workspace app, or standalone out-of-tree app
- **Existing tests**: any `tests/` directory, existing `testcase.yaml` files, pytest or shell harness
- **Board target**: from `$BOARD`, `envsetup.sh`, or `west build` history
- **Zephyr version**: check `$ZEPHYR_BASE/VERSION` or `west list zephyr`
- **Console output**: determine whether the board uses UART, RTT, or both for console output

If `west topdir` fails, check whether `ZEPHYR_BASE` is set or if `envsetup.sh` needs sourcing.

Before using any Twister parameter you're not sure about:

```bash
west twister --help
```

Do not copy stale parameters.

## Step 1 — Choose Test Layer

Pick the lowest-cost layer that covers the requirement. Never default to a higher layer.

| Layer | Platform | Use for |
|-------|----------|---------|
| **A — Unit** | `native_sim` + Ztest | Pure algorithms, parsers, state machines, ring buffers, packet codecs, boundary conditions, error handling, regressions |
| **B — Integration** | `native_sim` (or QEMU) + Ztest | Threads, work queues, semaphores, message queues, timers, shell commands, inter-module data flow |
| **C — App Interaction** | Twister with pytest/shell harness | Boot log checks, shell command execution, serial interaction, multi-step functional tests, Python-driven DUT tests |
| **D — Hardware** | Real board only | GPIO, SAADC, TIMER, GPPI, DMA, BLE RF, interrupt timing, peripheral drivers, power measurement, sensor data |

### Hardware coupling rule

If the module under test couples to hardware, propose the **minimum decoupling** needed:

1. Extract pure logic into a standalone `.c/.h`
2. Test the extracted logic at Layer A
3. Keep hardware interaction for Layer D

### Platform allow-list convention

When the project targets a specific board, use `native_sim/native/64` for simulation tests:

```yaml
platform_allow: native_sim/native/64
integration_platforms:
  - native_sim/native/64
```

Use `native_sim/native/64` (64-bit host) for most algorithm and integration tests — it matches modern host architectures and catches pointer-width bugs. Use `native_sim` (32-bit) only when the test must verify `sizeof(void *) == 4` behavior, e.g. packing assumptions in wire protocols or pointer-to-int casts.

## Step 2 — Create Test Structure

Standard layout for a module test:

```
tests/<module-name>/
├── CMakeLists.txt
├── prj.conf
├── testcase.yaml
└── src/
    └── main.c
```

When Python-driven testing is needed, add:

```
tests/<module-name>/
├── pytest/
│   └── test_<feature>.py
├── testcase.yaml       # ← add harness: pytest
└── ...
```

Before creating files:

1. Check existing tests in the repo for style and naming conventions
2. Match the pattern — same license header, same include style, same directory naming
3. Reuse existing helper functions if tests share utilities

### Source inclusion pattern

For out-of-tree algorithm modules, include source files directly in the test `CMakeLists.txt`:

```cmake
target_include_directories(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/<module>
)
target_sources(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/<module>/<module>.c
  src/main.c
)
```

Do not link the full application; include only the files under test and their direct dependencies.

### Kconfig

Start minimal:

```
CONFIG_ZTEST=y
```

Add only what the test actually needs. Never copy the full application `prj.conf`.

## Step 3 — Write Tests

### Test design checklist

For every test function, consider:

- [ ] Normal input
- [ ] Min and max values
- [ ] Boundary ± 1
- [ ] Empty / zero input
- [ ] Invalid / out-of-range input
- [ ] Repeated calls
- [ ] State reset between tests
- [ ] Timeout behavior
- [ ] Data interruption / gaps
- [ ] Buffer-full condition
- [ ] Regression for every fixed bug

For algorithm modules additionally:

- [ ] Deterministic input (known-good arrays)
- [ ] Noisy input
- [ ] Dropped samples
- [ ] Discontinuous timestamps
- [ ] Cold-start behavior
- [ ] Tracking state across calls
- [ ] Recovery after sustained rejection
- [ ] Fixed random seed (if applicable)
- [ ] Tolerance justified by algorithm precision / quantization

### Tolerance rule

Never relax assertions to make tests pass. Tolerances must be explicitly justified:

```c
/* Filter passband ripple: ±2% for 16-bit fixed-point with 8-bit coefficient */
zassert_within(output, expected, expected * 2 / 100,
               "passband output exceeds quantization tolerance");
```

### Ztest suite pattern

```c
#include <zephyr/ztest.h>
#include "module_under_test.h"

ZTEST_SUITE(my_module, NULL, /*setup=*/NULL, /*before=*/NULL, /*after=*/NULL, /*teardown=*/NULL);

ZTEST(my_module, test_normal_operation)
{
    /* arrange, act, assert */
}
```

ZTEST_SUITE signature: `(name, options, setup, before, after, teardown)`.

- `setup` (param 3): suite-level, called once, returns `void *` as shared fixture
- `before` (param 4): per-test, called before each test, receives fixture `void *`
- `after` (param 5): per-test, called after each test, receives fixture `void *`
- `teardown` (param 6): suite-level, called once at the end, receives fixture `void *`

Example using suite-level setup/teardown:

```c
static void *suite_setup(void)
{
    /* allocate shared state, returned as fixture */
    return &shared_state;
}

static void suite_teardown(void *fixture)
{
    /* cleanup */
}

ZTEST_SUITE(my_module, NULL, suite_setup, NULL, NULL, suite_teardown);
```

## Step 4 — Run Tests

### Twister (preferred for multi-scenario)

```bash
# Run all scenarios in a test directory
west twister -T tests/<module-name> -p native_sim

# Verbose output
west twister -T tests/<module-name> -p native_sim -v

# List available scenarios
west twister -T tests/<module-name> --list-tests

# Run a single scenario
west twister -T tests/<module-name> -p native_sim -s <scenario-name>

# Re-run previous failures
west twister -T tests/<module-name> -p native_sim -f

# Coverage report
west twister -T tests/<module-name> -p native_sim --coverage
```

### Direct build + run (single test app)

```bash
west build -b native_sim tests/<module-name> -p always
./build/zephyr/zephyr.exe
```

### Real hardware

Only for Layer D. Before executing, state:

- Board name
- Runner (jlink, openocd, etc.)
- Console output method (serial, RTT, or PTY bridge)
- Commands to be run
- Potential side effects (flash erase, reset)

```bash
west twister \
  -T tests/<module-name> \
  -p <board> \
  --device-testing \
  --device-serial /dev/ttyACM0
```

For boards that only output via RTT (no UART console): Twister expects a serial device. If no PTY adapter bridges RTT to a serial device, run the test as a standalone hardware verification step outside Twister.

## Step 5 — Diagnose Failures

When a test fails, **do not** immediately rewrite code. Follow this sequence:

1. **Read the output** — Twister log, build log, or runtime output
2. **Classify the failure**:
   - Configuration error (Kconfig / testcase.yaml)
   - Compilation error (missing header, undefined symbol)
   - Link error (unresolved function)
   - Runtime crash / hang
   - Assertion failure (wrong value)
   - Timeout
3. **Find the first actionable error message** — scroll past warnings to the first error
4. **Check `prj.conf`** — missing `CONFIG_*`?
5. **Check `CMakeLists.txt`** — missing source file or include path?
6. **Check `testcase.yaml`** — wrong platform, wrong tags, wrong harness, `filter` excluding target platform?
7. **Reproduce minimally** — single scenario, direct build
8. **If needed**: run `zephyr.exe` directly, use GDB, ASan, UBSan, or Valgrind

After fixing, re-run only the failed scenario and explain what changed.

For detailed troubleshooting: `read skill://zephyr-testing/references/troubleshooting.md`

## Step 6 — Report

After completing any test task, give a concise report:

```
Test target:      <module or function>
Test layer:       A/B/C/D
Files changed:    <list>
Run command:      <exact command>
Result:           PASS / FAIL / N/A
Failure reason:   <if applicable>
Hardware gaps:    <what still needs real hardware>
Next step:        <concrete action>
```

## Reference Documents

- **Templates**: `read skill://zephyr-testing/references/templates.md`
- **Troubleshooting**: `read skill://zephyr-testing/references/troubleshooting.md`
- **Algorithm test example**: `read skill://zephyr-testing/examples/algorithm-test-layout.md`
