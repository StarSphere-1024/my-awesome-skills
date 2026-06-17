# Zephyr Testing Troubleshooting

## `west topdir` fails

**Common cause**: Not inside a west workspace, or `ZEPHYR_BASE` not set.

**Check**:

```bash
echo "$ZEPHYR_BASE"
ls -la .west 2>/dev/null
cat .west/config 2>/dev/null
```

**Fix**:

- If `envsetup.sh` exists, source it first
- If no `.west/` in current dir, check parent directories
- For standalone apps: set `ZEPHYR_BASE` explicitly or use `west -z <topdir>`

---

## `west twister` not found

**Common cause**: Zephyr scripts not on `PATH`, or west version too old.

**Check**:

```bash
which west
west --version
python3 -m west twister --help
```

**Fix**:

- Source `envsetup.sh` or activate the Python venv that has `west` installed
- Update west: `pip install -U west`
- Ensure `ZEPHYR_BASE` is set correctly

---

## `native_sim` board not found

**Common cause**: Board roots not configured, or Zephyr version too old (native_sim ≥ 3.5).

**Check**:

```bash
west boards | grep native
ls $ZEPHYR_BASE/boards/native/
```

**Fix**:

- Verify `ZEPHYR_BASE` points to a Zephyr tree that includes `native_sim`
- If using out-of-tree board, check `BOARD_ROOT` in `CMakeLists.txt`
- Older Zephyr versions use `native_posix` instead of `native_sim`

---

## Twister doesn't find my test

**Common cause**: `testcase.yaml` not in expected location, wrong directory structure, or platform not matched.

**Check**:

```bash
# Verify testcase.yaml exists and is valid YAML
cat tests/<module-name>/testcase.yaml

# List what Twister sees
west twister -T tests/<module-name> --list-tests

# Check platform matching
west twister -T tests/<module-name> -p native_sim --list-tests
```

**Common fixes**:

- `testcase.yaml` must be in the test app root (same level as `CMakeLists.txt`)
- `tests:` key must be present and non-empty
- `platform_allow` must include the target platform (or be absent)
- Use `--list-tests` to verify Twister finds the scenario before running

---

## `testcase.yaml` format error

**Common cause**: Indentation or structure doesn't match Twister expectations.

**Check**:

```bash
# Validate YAML (use twister if pyyaml not installed)
python3 -c "import yaml" 2>/dev/null && python3 -c "import yaml; yaml.safe_load(open('tests/<module-name>/testcase.yaml'))" || west twister -T tests/<module-name> --list-tests
```

**Fix**: Ensure this structure:

```yaml
tests:
  scenario.name:          # ← indented 2 spaces under `tests:`
    platform_allow:       # ← indented 4 spaces under scenario name
      - native_sim/native/64
    tags:
      - my_tag
```

Common mistakes:

- Missing `tests:` top-level key
- Using tabs instead of spaces
- Wrong indentation depth
- Empty scenario name

---

## Ztest suite doesn't run

**Common cause**: Suite name mismatch, missing `ZTEST_SUITE` macro, or link issue.

**Check**:

```bash
# Check the built binary for suite registration
nm build/zephyr/zephyr.exe | grep z_test_suite

# Check build output for warnings
west build -b native_sim tests/<module-name> -p always 2>&1 | grep -i "warn\|error"
```

**Common fixes**:

- Ensure `ZTEST_SUITE(name, ...)` is in the test source
- Ensure `CONFIG_ZTEST=y` in `prj.conf`
- Suite name in `ZTEST_SUITE` must match the `ZTEST(name, ...)` calls
- If using `ZTEST_SUITE` with `before`/`after`, ensure function signatures are correct:
  - `before`: `static void *before(void)` or `static void before(void *f)`
  - `after`: `static void after(void *f)`

---

## Missing header during compilation

**Common cause**: Include path not set in `CMakeLists.txt`.

**Check**:

```bash
# Find where the header lives
find . -name "module_under_test.h" -not -path "*/build/*"

# Check what include dirs are configured
grep -n "target_include_directories" tests/<module-name>/CMakeLists.txt
```

**Fix**: Add to test `CMakeLists.txt`:

```cmake
target_include_directories(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/path/to/module
)
```

If the header depends on generated files (devicetree, Kconfig), you may need additional include paths:

```cmake
target_include_directories(app PRIVATE
  ${ZEPHYR_BASE}/include
  ${CMAKE_BINARY_DIR}/zephyr/include/generated
)
```

---

## Link error — undefined function

**Common cause**: Source file not included in the test build.

**Check**:

```bash
# Find the file that defines the missing function
grep -rn "function_name" src/ --include="*.c" | grep -v "build/"

# Check what sources the test includes
grep -n "target_sources" tests/<module-name>/CMakeLists.txt
```

**Fix**: Add the source file to `target_sources`:

```cmake
target_sources(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/../../src/module/missing_file.c
  src/main.c
)
```

If the function is in a library, add `target_link_libraries`.

---

## Kconfig dependency not satisfied

**Common cause**: Module requires a Kconfig symbol that's not enabled.

**Check**:

```bash
# Find the Kconfig dependency
grep -rn "depends on\|select" $ZEPHYR_BASE/modules/Kconfig.* | grep "REQUIRED_SYMBOL"

# Check what's enabled
cat build/zephyr/.config | grep REQUIRED_SYMBOL
```

**Fix**: Add to test `prj.conf`:

```
CONFIG_REQUIRED_SYMBOL=y
```

Or pass as extra args in `testcase.yaml`:

```yaml
extra_args: CONFIG_REQUIRED_SYMBOL=y
```

---

## Devicetree dependency fails on `native_sim`

**Common cause**: Test code references devicetree nodes that don't exist on `native_sim`.

**Check**:

```bash
# Check what DTS nodes native_sim has
cat $ZEPHYR_BASE/boards/native/native_sim/native_sim_native_64.dts 2>/dev/null

# Check if test code uses DT macros
grep -rn "DT_\|DT_NODE\|DT_LABEL\|DT_ALIAS" tests/<module-name>/src/
```

**Fix options**:

1. **Decouple from devicetree**: Move the algorithm to a standalone `.c/.h` and test that instead
2. **Add overlay**: Create `tests/<module-name>/boards/native_sim_native_64.overlay` with fake DTS nodes
3. **Filter**: In `testcase.yaml`, use `filter` to exclude native_sim and only run on real hardware:
   ```yaml
   filter: not CONFIG_NATIVE_SIM
   ```

---

## Test runs timeout

**Common cause**: Test takes longer than the default timeout (60s), or test hangs.

**Check**:

```bash
# Run with verbose to see where it hangs
west twister -T tests/<module-name> -p native_sim -s <scenario> -v

# Try running the binary directly to see output
west build -b native_sim tests/<module-name> -p always
./build/zephyr/zephyr.exe
```

**Fix**:

- Increase timeout in `testcase.yaml`:
  ```yaml
  tests:
    my_module.long_test:
      timeout: 300
  ```
- If the test hangs, check for:
  - Infinite loops in test code
  - Blocking `k_sleep()` calls
  - Missing `k_sem_give()` in mock callbacks
  - Shell harness waiting for a line that never prints

---

## No serial output on real hardware

**Common cause**: Wrong port, wrong baud rate, or console not configured.

**Check**:

```bash
# List serial devices
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# Check board documentation for correct console UART
# Check if RTT is used instead of UART

# Test with screen or minicom
screen /dev/ttyACM0 115200
```

**Fix**:

- Verify the serial port matches the board's console UART
- Check `prj.conf` has `CONFIG_UART_CONSOLE=y` (or appropriate Kconfig)
- Some boards use RTT for console — check for `CONFIG_RTT_CONSOLE=y`. If the board is RTT-only, see "RTT-only boards and Twister" below.

---

## RTT-only boards and Twister

**Problem**: Twister expects serial output but the board only outputs via RTT.

**Check**:

```bash
# Does the project have a PTY adapter for RTT?
find . -name "*rtt*pty*" -o -name "*rtt*serial*" 2>/dev/null
# Is there a J-Link RTT script?
find . -name "*rtt*.py" 2>/dev/null
```

**Options**:

1. **If a PTY adapter exists**: Use `--device-serial-pty` in Twister
2. **If no adapter**: Build and flash the test binary, then read RTT output manually (e.g. with J-Link RTT Viewer or a project RTT script). Document this as a limitation in `testcase.yaml` with `build_only: true`

```yaml
tests:
  my_module.hardware:
    platform_allow: <board>
    build_only: true
    tags:
      - hardware
```
---

## Coverage report not generated

**Common cause**: Missing `CONFIG_COVERAGE` or wrong coverage tool path.

**Check**:

```bash
# Verify gcovr is installed
which gcovr
gcovr --version

# Verify build has coverage enabled
cat build/zephyr/.config | grep COVERAGE
```

**Fix**:

```bash
# Install gcovr if missing
pip install gcovr

# Build with coverage
west twister -T tests/<module-name> -p native_sim \
  --coverage \
  -DCONFIG_COVERAGE=y

# Check output location
ls twister-out/coverage/ 2>/dev/null
ls twister-out/**/coverage.html 2>/dev/null
```

If `--coverage` flag is not recognized, check your Twister version:

```bash
west twister --help | grep coverage
```

---

## ASan / UBSan / Valgrind with `native_sim`

### AddressSanitizer (ASan)

```bash
# Build with ASan
west build -b native_sim tests/<module-name> -p always \
  -DCONFIG_ASAN=y

# Run
./build/zephyr/zephyr.exe
```

In `prj.conf`:

```
CONFIG_ASAN=y
```

### UndefinedBehaviorSanitizer (UBSan)

```bash
west build -b native_sim tests/<module-name> -p always \
  -DCONFIG_UBSAN=y

./build/zephyr/zephyr.exe
```

In `prj.conf`:

```
CONFIG_UBSAN=y
```

### Valgrind

```bash
west build -b native_sim tests/<module-name> -p always

valgrind --leak-check=full --track-origins=yes ./build/zephyr/zephyr.exe
```

No special Kconfig needed — Valgrind works on any native binary.

### Notes

- ASan and UBSan are compile-time instruments; they add overhead but catch bugs at the source
- Valgrind is runtime-only; slower but no recompilation needed
- Combining ASan + Valgrind is redundant; pick one
- For `native_sim` tests run through Twister, use `extra_args: CONFIG_ASAN=y` in `testcase.yaml`

---

## Narrowing to a single scenario

```bash
# List all scenarios in a test
west twister -T tests/<module-name> --list-tests

# Run only one
west twister -T tests/<module-name> -p native_sim -s <scenario-name>

# Run directly without Twister
west build -b native_sim tests/<module-name> -p always
./build/zephyr/zephyr.exe --test-case <scenario-name>   # Ztest CLI
```

---

## Re-running only failures

```bash
# Twister stores results in twister-out/
# Re-run only failed tests
west twister -T tests/<module-name> -p native_sim -f

# Or specify the report file
west twister -T tests/<module-name> -p native_sim \
  --last-failed twister-out/twister.json
```
