---
name: zephyr-clangd
description: Configure clangd language server for Zephyr RTOS projects with cross-compilation toolchains. Use when setting up clangd for Zephyr, nRF Connect SDK, or ARM cross-compilation projects, or when clangd shows errors like "Unknown Arm architecture profile" or "failed to resolve include".
---

# Zephyr clangd Configuration

## Quick Start

1. Generate `compile_commands.json` with `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`
2. Create symlink: `ln -sf build/<app>/compile_commands.json .`
3. Detect toolchain paths and target triple from user environment
4. Create `.clangd` config using detected values
5. Create `.vscode/settings.json` with `--query-driver`
6. Restart clangd in editor

## Workflow

### Step 1: Detect Environment

Before configuring, gather these from the user's environment:

```bash
# 1. Board (from env or west build command)
echo $BOARD

# 2. Cross-compiler path
which arm-*-gcc  # or from ZEPHYR_SDK_INSTALL_DIR

# 3. Target triple (from compiler)
arm-zephyr-eabi-gcc -dumpmachine

# 4. GCC version (from compiler path)
arm-zephyr-eabi-gcc -dumpversion

# 5. Built-in include paths
arm-zephyr-eabi-gcc -E -x c -v /dev/null 2>&1 | awk '/search starts here/,/End of search/' | grep "^\s/"

# 6. SDK install dir
echo $ZEPHYR_SDK_INSTALL_DIR
```

**Target triple mapping** (use `arm-*-gcc -dumpmachine` to get exact value):
| Architecture | Target Triple |
|---|---|
| Cortex-M0/M0+ | `thumbv6m-none-eabi` |
| Cortex-M3 | `thumbv7m-none-eabi` |
| Cortex-M4/M7 (no FPU) | `thumbv7em-none-eabi` |
| Cortex-M4/M7 (with FPU) | `thumbv7em-none-eabihf` |
| Cortex-M33 | `thumbv8m.main-none-eabi` |
| Cortex-M33 (with FPU) | `thumbv8m.main-none-eabihf` |
| Cortex-M55 | `thumbv8.1m.main-none-eabihf` |

### Step 2: Generate compile_commands.json

Add `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` to the build command:

```bash
# In envsetup.sh, add to wbuild function:
-DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

Or run manually:
```bash
source envsetup.sh
west build --build-dir build . --pristine --board $BOARD -- -DCMAKE_EXPORT_COMPILE_COMMANDS=ON [other flags]
```

### Step 3: Create Symlink

```bash
ln -sf build/<app-name>/compile_commands.json .
```

The `<app-name>` is the CMake project name (check `build/` directory for the subfolder name).

### Step 4: Create .clangd

Create `.clangd` in project root. Use detected values:

```yaml
CompileFlags:
  Add:
    - "-Wno-unknown-warning-option"
    - "--target=<DETECTED_TARGET_TRIPLE>"  # from arm-*-gcc -dumpmachine
    # Include paths from: arm-*-gcc -E -x c -v /dev/null
    - "-isystem"
    - "<GCC_INCLUDE_PATH>/include"           # e.g. .../lib/gcc/arm-zephyr-eabi/<VER>/include
    - "-isystem"
    - "<GCC_INCLUDE_FIXED_PATH>/include-fixed" # e.g. .../lib/gcc/arm-zephyr-eabi/<VER>/include-fixed
    - "-isystem"
    - "<SYSROOT>/sys-include"                # e.g. .../arm-zephyr-eabi/arm-zephyr-eabi/sys-include
    - "-isystem"
    - "<SYSROOT>/include"                    # e.g. .../arm-zephyr-eabi/arm-zephyr-eabi/include
  Remove:
    - "-mcpu=*"
    - "-mthumb"
    - "-mabi=*"
    - "-mfpu=*"
    - "-mfloat-abi=*"
    - "-mfp16-format=*"
    - "-march=*"
    - "-mtp=*"
    - "--specs=*"
    - "--param=*"
    - "--sysroot=*"
    - "-fno-defer-pop"
    - "-fno-reorder-functions"
    - "-fno-reorder-blocks"
    - "-fno-toplevel-reorder"
    - "-fno-pie"
    - "-fno-pic"
    - "-fno-common"
    - "-fno-asynchronous-unwind-tables"
    - "-fno-printf-return-value"
    - "-fno-strict-aliasing"
    - "-fmacro-prefix-map=*"
    - "-ffunction-sections"
    - "-fdata-sections"
    - "-fdiagnostics-color=*"
    - "-gdwarf-*"
    - "-gcc"

Diagnostics:
  UnusedIncludes: None
  Suppress:
    - "drv_unknown_argument"
    - "pp_file_not_found"
    - "pp_building_preamble"
```

### Step 5: Configure VS Code

Create `.vscode/settings.json` with `--query-driver` pointing to the cross-compiler:

```json
{
    "clangd.arguments": [
        "--query-driver=<CROSS_COMPILER_DIR>/*",
        "--header-insertion=never",
        "--background-index"
    ]
}
```

The `--query-driver` value should be a glob matching the cross-compiler binary:
- Find compiler dir: `dirname $(which arm-*-gcc)`
- Set to: `<compiler_dir>/*`

### Step 6: Restart clangd

- VS Code: `Ctrl+Shift+P` → "clangd: Restart language server"
- Neovim: `:LspRestart`

## Common Issues

### "Unknown Arm architecture profile"

**Cause**: clangd doesn't know the target architecture.

**Fix**: Add `--target=<triple>` to `.clangd` CompileFlags.Add. Get triple from `arm-*-gcc -dumpmachine`.

### "Unknown argument: '-mfp16-format=ieee'" (or other -m flags)

**Cause**: ARM-specific compiler flags not recognized by clangd.

**Fix**: Add the flag pattern to `.clangd` CompileFlags.Remove (already in template above).

### "Failed to get an entry for resolved path '' from include <stdio.h>"

**Cause**: clangd can't find system headers for the cross-compiler.

**Fix**:
1. Add `--query-driver=<compiler-dir>/*` to `.vscode/settings.json`
2. Add GCC built-in include paths as `-isystem` in `.clangd`

### "Main file cannot be included recursively when building a preamble"

**Cause**: A header file includes itself (circular include).

**Fix**: Search for self-includes:
```bash
# Find the offending file from clangd error, then check:
grep -rn '#include "filename.h"' path/to/filename.h
```

### Errors about undeclared functions (strcat, strlen, etc.)

**Cause**: System headers not found, so library functions aren't declared.

**Fix**: Ensure `--query-driver` is set correctly and include paths are in `.clangd`.

## Reference Commands

```bash
# Find cross-compiler
find $ZEPHYR_SDK_INSTALL_DIR -name "arm-*-gcc" -type f 2>/dev/null

# Get target triple
arm-zephyr-eabi-gcc -dumpmachine

# Get GCC version (used in include path)
arm-zephyr-eabi-gcc -dumpversion

# Get built-in include paths
arm-zephyr-eabi-gcc -E -x c -v /dev/null 2>&1 | awk '/search starts here/,/End of search/' | grep "^\s/"

# Get sysroot
arm-zephyr-eabi-gcc -print-sysroot

# Find all compile_commands.json in build
find build -name "compile_commands.json" -type f

# Detect board from west build args or environment
echo $BOARD
grep -r "BOARD" envsetup.sh CMakeLists.txt
```
