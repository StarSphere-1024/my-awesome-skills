---
name: linux-gdb-debugger
description: Use for Linux C/C++ GDB crash, core dump, and hang debugging.
metadata:
  category: debugging
  tags: linux, c, cpp, gdb, core-dump
---

# Linux GDB Debugger

Use GDB evidence before editing Linux user-space C/C++ crash or hang bugs.

## Scope

Use for local Linux executables, native tests, Linux core files, and user-provided Linux PIDs. This includes SIGSEGV, SIGABRT, bad pointers, memory corruption, deadlocks, infinite loops, JNI/native-extension crashes, and logic bugs that need bounded stepping.

Do not use for Windows, macOS/LLDB, MCU/OpenOCD/pyOCD/J-Link, RTOS targets, Linux kernel/module debugging, or remote `gdbserver` workflows.

## Workflow

1. Identify the exact executable and reproduction command.
2. Build with debug symbols when possible.
3. Run the matching script from this skill's `scripts/` directory.
4. Read the generated `.debug/` GDB log.
5. Identify the failure, crashing frame, first application frame, arguments, locals, thread state, and suspicious value or pointer.
6. Make the smallest code change consistent with the evidence.
7. Rebuild and rerun the original command.
8. Rerun GDB or the test to verify the failure is gone.

If symbols are missing or values show `<optimized out>`, say so and prefer Debug or RelWithDebInfo builds.

## Build

For direct C/C++ builds, prefer:

```bash
CFLAGS="-g -O0" CXXFLAGS="-g -O0"
```

For CMake:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

If optimization is required to reproduce:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

## Scripts

- Crash or native test crash: `scripts/gdb-crash.sh <executable> [args...]`
- Stdin-driven crash: `STDIN=input.txt scripts/gdb-crash.sh <executable> [args...]`
- Core file: `scripts/gdb-core.sh <executable> <core-file>`
- Hang/deadlock: `scripts/gdb-hang.sh <executable> [args...]`
- Existing process hang: `PID=<pid> scripts/gdb-hang.sh [matching-executable]`
- Bounded stepping: `BREAK=main STEPS=30 MODE=next scripts/gdb-step.sh <executable> [args...]`

For noisy hang logs, use `BT_COMMAND="thread apply all bt 30"` or `FRAME_ARGS=scalars`.

## References

Load only what is needed:

- `references/diagnosis-playbook.md` for root-cause workflow.
- `references/gdb-command-patterns.md` for breakpoints, watchpoints, and stepping.
- `references/common-native-bugs.md` for failure signatures.

## Safety

- Do not use `sudo` or destructive commands.
- Do not attach to arbitrary PIDs unless the user provided the PID or this session launched it.
- Keep GDB logs and command files under `.debug/`.
- Bound stepping with `STEPS`; prefer breakpoints/watchpoints over long step runs.
- Do not continue indefinitely on hangs.
- Do not delete core files or logs unless asked.
