---
name: zephyr-clangd
description: Fix clangd/LSP for Zephyr and nRF Connect SDK projects using compile_commands.json and query-driver. Use for broken includes, bogus Zephyr macro errors, wrong ARM targets, stale NCS toolchain paths, or bad go-to-definition.
metadata:
  category: embedded
  tags: zephyr, ncs, clangd, lsp
---

# Zephyr clangd Configuration

Use this skill to make clangd parse Zephyr/NCS firmware with the same compile flags as the real build. The compile database is the source of truth; avoid reconstructing target triples, sysroots, generated include paths, and board macros by hand.

## Core rule

Prefer this model:

```text
Zephyr build -> build/<app>/compile_commands.json -> clangd CompilationDatabase + query-driver
```

Avoid this model unless there is no working compile database:

```text
hand-written --target + hand-written -isystem GCC paths + stripped ARM flags
```

Hand-written target/include flags go stale when NCS changes toolchain hashes, GCC versions, boards, overlays, generated headers, or build directories. They can also hide the real failure: clangd did not load the compile database or could not execute the cross compiler through `--query-driver`.

## Quick start

1. Build with `CMAKE_EXPORT_COMPILE_COMMANDS=ON` so `build/<app>/compile_commands.json` exists.
2. Locate the real build subdirectory containing the compile database.
3. Configure `.clangd` with `CompileFlags.CompilationDatabase: build/<app>`.
4. Configure the editor with both `--compile-commands-dir` and `--query-driver`.
5. Verify with `clangd --check` on a small source file before trusting editor diagnostics.
6. Restart clangd in the editor.

A root-level `compile_commands.json` symlink can be useful for legacy tools, but do not rely on it as the only clangd configuration. Point clangd at the real build directory explicitly.

## Step 1: Locate the compile database

Find candidate compile databases:

```bash
find build -name compile_commands.json -type f
```

Prefer the one whose entries point at the current repo's source files. In common sysbuild/NCS app builds, the useful path is often:

```text
build/<app-name>/compile_commands.json
```

Examples:

```text
build/fw260528/compile_commands.json
build/blebasefw/compile_commands.json
```

If there are multiple compile databases, inspect the first entry and choose the one where:

- `directory` is the application build directory, not only a bootloader/radio child image.
- `file` points to the app source tree, such as `src/main.c`.
- `command` uses the Zephyr SDK cross compiler, such as `arm-zephyr-eabi-gcc`.

## Step 2: Configure `.clangd`

Create or update `.clangd` in the project root. Replace `<app-name>` with the build subdirectory found in Step 1.

```yaml
CompileFlags:
  CompilationDatabase: build/<app-name>
  Add:
    - "-Wno-unknown-warning-option"
  Remove:
    - "-mfp16-format=*"
    - "--specs=*"
    - "--param=*"
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

### Do not remove target-defining flags

Do not put these in `CompileFlags.Remove` for Zephyr/NCS ARM firmware:

```yaml
- "-mcpu=*"
- "-mthumb"
- "-mabi=*"
- "-mfpu=*"
- "-mfloat-abi=*"
- "-march=*"
- "-mtp=*"
- "--sysroot=*"
```

Those flags carry the actual target architecture and system root from the Zephyr build. Removing them can make clangd fall back to the wrong CPU, such as `arm7tdmi`/`armv4t`, and then report misleading errors like `Unknown Arm architecture profile`.

### Do not hand-write GCC include paths by default

Do not add Zephyr SDK GCC built-in include paths like this unless query-driver cannot be made to work:

```yaml
- "-isystem"
- "/home/.../arm-zephyr-eabi/lib/gcc/.../include"
```

Instead, configure `--query-driver` so clangd runs the real compiler and extracts system include paths automatically.

### Do not hand-write `--target` by default

Do not add this by default:

```yaml
- "--target=thumbv8m.main-none-eabi"
```

The compile database plus compiler name normally provides a better target. A hand-written clang-style `--target` can also interfere with GCC system include extraction.

## Step 3: Configure the editor

For VS Code, create or update `.vscode/settings.json`:

```json
{
    "clangd.arguments": [
        "--compile-commands-dir=${workspaceFolder}/build/<app-name>",
        "--query-driver=<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/*",
        "--header-insertion=never",
        "--background-index"
    ]
}
```

Adjust the query-driver path for the user's NCS/Zephyr SDK location. Prefer a glob over a fixed NCS toolchain hash:

```text
Good: <ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/*
Risky: <ncs-root>/toolchains/2ac5840438/opt/zephyr-sdk/arm-zephyr-eabi/bin/*
```

NCS updates can change the hash directory while `compile_commands.json` still points at the current toolchain. A hash-specific query-driver can silently become stale.

For Neovim, Zed, or other editors, pass the same clangd arguments through that editor's LSP configuration:

```text
--compile-commands-dir=<repo>/build/<app-name>
--query-driver=<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/*
--header-insertion=never
--background-index
```

## Step 4: Verify from the terminal

Use a small source file first. Large `src/main.c` files can spend a long time in clangd's `Testing features at each token` phase.

```bash
clangd --check=src/app_ab.c \
  --compile-commands-dir=build/<app-name> \
  --query-driver=<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/*
```

A healthy setup shows these facts:

```text
Loaded compilation database from .../build/<app-name>/compile_commands.json
System includes extractor: successfully executed .../arm-zephyr-eabi-gcc
got target: "arm-zephyr-eabi"
-triple thumbv8m.main-zephyr-unknown-eabi
-target-cpu cortex-m33
```

The exact triple may differ by board and float ABI. The important facts are:

- clangd loaded the app compile database.
- clangd executed the cross compiler through query-driver.
- clangd did not fall back to `/usr/bin/clang`.
- clangd sees the intended ARM/Thumb CPU, not a generic host or wrong legacy ARM CPU.

Then check editor/LSP diagnostics for representative files.

## Troubleshooting

### clangd falls back to `/usr/bin/clang`

Symptoms:

```text
Failed to find compilation database
Generic fallback command is: ... /usr/bin/clang ...
```

Fix:

1. Confirm `build/<app-name>/compile_commands.json` exists.
2. Set `.clangd` `CompileFlags.CompilationDatabase: build/<app-name>`.
3. Add editor arg `--compile-commands-dir=${workspaceFolder}/build/<app-name>`.
4. Do not rely only on a root `compile_commands.json` symlink.

### `Unknown Arm architecture profile`

Usually this means clangd lost the real target flags, not that you should add a hand-written `--target`.

Check:

1. Is clangd loading the app compile database?
2. Did `.clangd` remove `-mcpu=*`, `-mthumb`, `-mabi=*`, `-mfpu=*`, `-mfloat-abi=*`, `--sysroot=*`, or similar target/sysroot flags?
3. Does `clangd --check` show a wrong internal target such as `armv4t` or `arm7tdmi`?

Fix:

- Restore target-defining flags by removing those patterns from `CompileFlags.Remove`.
- Use `CompilationDatabase` and `query-driver` rather than hand-written `--target`/`-isystem` flags.

### `unknown argument: '-mfp16-format=ieee'`

Fix:

```yaml
CompileFlags:
  Remove:
    - "-mfp16-format=*"
```

This one is commonly safe to remove because clangd/clang may not accept GCC's `-mfp16-format=ieee`, while the remaining architecture flags still describe the target.

### System headers or Zephyr headers cannot be resolved

Symptoms:

```text
failed to resolve include
Failed to get an entry for resolved path '' from include <...>
strcat/strlen undeclared
Zephyr macros like LOG_MODULE_REGISTER or K_SEM_DEFINE look broken
```

Fix in this order:

1. Ensure clangd loaded `build/<app-name>/compile_commands.json`.
2. Ensure `--query-driver` matches the actual cross compiler path from the compile command.
3. Prefer a toolchain glob over a fixed NCS hash.
4. Only as a last resort, add GCC built-in `-isystem` paths manually.

### clangd self-test reports `tweak: SwapBinaryOperands` overlap

Example:

```text
tweak: SwapBinaryOperands ==> FAIL: The new replacement overlaps with an existing replacement.
```

This can happen in `clangd --check` around Zephyr macros such as `K_MSEC()` or `K_SEM_DEFINE()`. Do not treat it as a configuration failure by itself. Prefer LSP diagnostics and the earlier `Loaded compilation database` / `System includes extractor` / target facts for setup validation.

### LSP line numbers or go-to-definition are obviously wrong

Symptoms:

- file symbols report line numbers that do not match the on-disk file;
- go-to-definition jumps to unrelated Zephyr macros;
- diagnostics disappear but navigation remains stale.

Fix:

1. Save all buffers in the editor.
2. Restart clangd.
3. Clear/rebuild clangd background index if the editor exposes that action.
4. Re-run `clangd --check` with the explicit build directory.

## Reference commands

Use these to inspect the environment. Treat them as diagnostics, not as values to hard-code into `.clangd` unless needed for a fallback.

```bash
# Find compile databases
find build -name compile_commands.json -type f

# Inspect the compiler used by the build
head -n 20 build/<app-name>/compile_commands.json

# Check compiler target reported by GCC
<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc -dumpmachine

# Check GCC system include extraction manually
<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc -E -x c -v /dev/null

# Verify clangd setup
clangd --check=src/app_ab.c \
  --compile-commands-dir=build/<app-name> \
  --query-driver=<ncs-root>/toolchains/*/opt/zephyr-sdk/arm-zephyr-eabi/bin/*
```

If working in a coding harness with specialized file/search tools, use those tools for file discovery and reading instead of shelling out for `find`, `grep`, or `head`. The shell examples above are for users configuring editors directly.
