# Zephyr Testing Templates

Copy and adapt. **Fields marked `<!-- ADAPT -->` must be changed for your project.**

---

## 1. Minimal Ztest `src/main.c`

```c
/*
 * SPDX-License-Identifier: Apache-2.0
 * <!-- ADAPT: update year and copyright holder -->
 * Copyright (c) 2026
 */

#include <zephyr/ztest.h>

/* <!-- ADAPT: include the header for the module under test --> */
#include "module_under_test.h"

/* <!-- ADAPT: rename the suite to match your module --> */
ZTEST_SUITE(my_module, NULL, NULL, NULL, NULL, NULL);

/* <!-- ADAPT: add test cases --> */
ZTEST(my_module, test_basic)
{
    int result = my_function(42);
    zassert_equal(result, 0, "expected 0, got %d", result);
}
```

---

## 2. Minimal `CMakeLists.txt`

```cmake
# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(my_module_test)  # <!-- ADAPT: project name -->

target_include_directories(app PRIVATE
  # <!-- ADAPT: path to module header directory -->
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/my_module
)

target_sources(app PRIVATE
  # <!-- ADAPT: source files under test (NOT the full application) -->
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/my_module/my_module.c
  src/main.c
)
```

---

## 3. Minimal `prj.conf`

```
CONFIG_ZTEST=y
# <!-- ADAPT: add only what the test actually needs -->
```

Common additions:

```
# If module uses logging
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3

# If module uses heap
CONFIG_HEAP_MEM_POOL_SIZE=4096

# If module uses floating point
CONFIG_FPU=y

# If module uses CMSIS DSP
CONFIG_CMSIS_DSP=y
```

---

## 4. Minimal `testcase.yaml`

```yaml
tests:
  # <!-- ADAPT: scenario name — use dotted notation: module.scenario -->
  my_module.basic:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module     # <!-- ADAPT: tag matching your module -->
```

---

## 5. Multi-scenario `testcase.yaml`

```yaml
tests:
  # <!-- ADAPT: each scenario tests a distinct aspect -->
  my_module.init:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
    extra_args: EXTRA_CONF_FILE=init.conf  # optional per-scenario config

  my_module.process:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module

  my_module.error_handling:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
      - negative

  # Example: pytest harness scenario
  my_module.integration:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
    harness: pytest
    harness_config:
      pytest_root:
        - pytest/test_integration.py

  # Example: shell harness scenario
  my_module.shell_cmd:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
    harness: shell
    harness_config:
      type: one_line
      regex:
        - "my_shell_cmd executed: (.*)"
```

### testcase.yaml field reference

| Field | Purpose |
|-------|---------|
| `tests:<name>` | Scenario name (dot-separated) |
| `platform_allow` | Platforms this test can run on |
| `integration_platforms` | Default CI platforms |
| `tags` | Filtering tags |
| `harness` | `ztest` (default), `pytest`, `shell`, `console` |
| `harness_config` | Harness-specific config |
| `extra_args` | Extra CMake or Kconfig args |
| `filter` | CMake filter expression |
| `timeout` | Test timeout in seconds (default 60) |
| `slow` | Mark as slow (skipped in quick runs) |
| `build_only` | Build but don't run |

---

## 6. Pytest Harness

### Directory structure

```
tests/<module-name>/
├── CMakeLists.txt
├── prj.conf
├── testcase.yaml
├── src/
│   └── main.c          # C test app that prints expected output
└── pytest/
    └── test_<feature>.py
```

### `testcase.yaml` snippet

```yaml
tests:
  my_module.pytest_example:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
    harness: pytest
    harness_config:
      pytest_root:
        - pytest/test_feature.py
```

### Minimal `pytest/test_feature.py`

```python
# SPDX-License-Identifier: Apache-2.0

import pytest

# <!-- ADAPT: import the correct fixture module -->
# Available fixtures depend on Zephyr version.
# Common: pytest-twister-harness provides dut fixture.

def test_shell_command(dut):
    """Example: send shell command and check output."""
    # <!-- ADAPT: match your shell command and expected output -->
    dut.readlines_until(regex='.*uart:~$', timeout=10)
    dut.write('my_cmd')
    lines = dut.readlines_until(regex='.*result=ok.*', timeout=5)
    assert any('result=ok' in line for line in lines)
```

### Harness fixtures (Zephyr ≥ 3.5)

The `dut` fixture provides:

| Method | Purpose |
|--------|---------|
| `dut.write(line)` | Send a line to the DUT |
| `dut.readlines_until(regex, timeout)` | Read until regex matches or timeout |
| `dut.readlines()` | Read all available lines |

Check your Zephyr version for exact API. Run:

```bash
find $ZEPHYR_BASE -path "*/twister_harness/*" -name "*.py" | head -5
```

---

## 7. Shell Harness

### `testcase.yaml` snippet

```yaml
tests:
  my_module.shell_example:
    platform_allow: native_sim/native/64
    integration_platforms:
      - native_sim/native/64
    tags:
      - my_module
    harness: shell
    harness_config:
      type: one_line
      regex:
        - "version: (.+)"
```

### C side — print expected line

In `src/main.c`, ensure the app prints the line the harness regex matches:

```c
#include <zephyr/kernel.h>

void main(void)
{
    printk("version: %s\n", "1.0.0");
}
```

### Multi-regex example

```yaml
harness: shell
harness_config:
  type: multi_line
  ordered: true
  regex:
    - "boot: ok"
    - "sensor: ready"
    - "test: PASS"
```

---

## 8. Real Hardware Test Commands

### Single board via serial

```bash
# <!-- ADAPT: board, serial port, and test path -->
west twister \
  -T tests/<module-name> \
  -p <board> \
  --device-testing \
  --device-serial /dev/ttyACM0 \
  -v
```

### Single board via RTT (if RTT-to-serial bridge exists)

```bash
# <!-- ADAPT: only if project has a PTY adapter for RTT -->
west twister \
  -T tests/<module-name> \
  -p <board> \
  --device-testing \
  --device-serial-pty /path/to/rtt_pty_adapter.sh \
  -v
```

If no RTT-to-serial bridge exists, do not use Twister for this board. Run the test binary directly and capture RTT output with project RTT tools.

### Direct build and flash

```bash
# Build
west build -b <board> tests/<module-name> -p always

# Flash (check runner from build output or board documentation)
west flash --runner jlink
```

---

## 9. Hardware Map

### File format (`hardwaremap.yaml`)

```yaml
# <!-- ADAPT: paths, IDs, and baud rates to match your hardware -->
- platform: nrf54l15dk/nrf54l15/cpuapp
  id: "001050012345"          # J-Link serial number or board ID
  serial: /dev/ttyACM0
  baud: 115200
  runner: jlink

- platform: nrf54l15dk/nrf54l15/cpuapp
  id: "001050012346"
  serial: /dev/ttyACM2
  baud: 115200
  runner: jlink
```

### Usage

```bash
west twister \
  -T tests/<module-name> \
  --device-testing \
  --hardware-map hardwaremap.yaml \
  -v
```

### Generating a hardware map

```bash
# Auto-detect connected boards
west twister --generate-hardware-map hardwaremap.yaml
```

Review and edit the generated file before use.

---

## 10. Coverage

### Generate coverage with Twister

```bash
west twister \
  -T tests/<module-name> \
  -p native_sim \
  --coverage \
  --coverage-tool gcovr
```

Output: `twister-out/coverage/` with HTML and/or XML reports.

### Direct gcov/lcov (after running a native_sim build)

```bash
# Build with coverage flags
west build -b native_sim tests/<module-name> -p always \
  -DCONFIG_COVERAGE=y

# Run
./build/zephyr/zephyr.exe

# Generate report
gcovr --root . --filter src/ -e '.*tests/.*' --html -o coverage.html
```

### Coverage flags for native_sim

In `prj.conf` or `extra_args`:

```
CONFIG_COVERAGE=y
CONFIG_COVERAGE_GCOV=y
```

Or pass via command line:

```bash
west twister -T tests/<module-name> -p native_sim \
  --coverage \
  -DCONFIG_COVERAGE=y
```

### Viewing the report

```bash
# If HTML generated
xdg-open twister-out/coverage/coverage.html
# Or
xdg-open coverage.html
```
