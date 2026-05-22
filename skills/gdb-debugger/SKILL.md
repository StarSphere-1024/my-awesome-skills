---
name: gdb-debugger
description: Use this skill whenever debugging native C, C++, or mixed C/C++ programs with GDB, including segmentation faults, SIGABRT, core dumps, hangs, deadlocks, infinite loops, failing native tests, invalid pointers, memory corruption, stack traces, JNI/native-extension crashes, or low-level runtime failures. This skill enforces evidence-first debugging: reproduce the issue, collect bounded GDB evidence, inspect backtraces, locals, args, and threads, identify the first bad state, make the smallest fix, rebuild, and verify before concluding.
---

# GDB Debugger

Use GDB as the primary diagnostic source for native failures. Do not guess first.

## Trigger Scope

Use this skill for:

- SIGSEGV, SIGABRT, assertion failures, and "core dumped"
- Native C/C++ unit test crashes or hangs
- Null, invalid, dangling, or corrupted pointers
- Stack or heap corruption symptoms
- Deadlocks, blocking waits, infinite loops, and thread stalls
- Native library failures from JNI, Python extensions, or embedded Linux programs
- Logic bugs that require bounded stepping through native code

Do not use this skill for pure Python/JavaScript/frontend bugs unless native code is involved.

## Required Workflow

Before editing code:

1. Identify the exact executable and reproduction command.
2. Build with debug symbols when possible.
3. Run the matching script from this skill's `scripts/` directory.
4. Read the generated `.debug/` GDB log.
5. Explain the failure evidence:
   - signal or error
   - crashing frame
   - first relevant application frame
   - arguments and locals
   - thread state
   - suspicious pointer, value, ownership, or state transition
6. Make the smallest code change consistent with the evidence.
7. Rebuild and rerun the failing command.
8. Rerun GDB or the original test to verify the failure is gone.

If debug symbols are missing or values are shown as `<optimized out>`, say so and prefer a Debug or RelWithDebInfo rebuild.

## Build Guidance

Prefer debug builds:

```bash
CFLAGS="-g -O0" CXXFLAGS="-g -O0"
```

For CMake:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

If the issue only reproduces under optimization:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build
```

## Workflow Selection

- **Crash, SIGSEGV, SIGABRT, native test crash**: use `scripts/gdb-crash.sh <executable> [args...]`. For stdin-driven reproducers, use `STDIN=input.txt scripts/gdb-crash.sh <executable> [args...]`.
- **Core dump**: use `scripts/gdb-core.sh <executable> <core-file>`.
- **Hang, deadlock, infinite loop**: use `scripts/gdb-hang.sh <executable> [args...]`, or `PID=<pid> scripts/gdb-hang.sh [matching-executable]` only when the user provided the PID or this session launched it. If hang logs are too large, use `BT_COMMAND="thread apply all bt 30"` or `FRAME_ARGS=scalars`.
- **Logic bug requiring stepping**: use bounded stepping with `BREAK=main STEPS=30 MODE=next scripts/gdb-step.sh <executable> [args...]`.

For deeper diagnosis, load only the relevant reference:

- `references/diagnosis-playbook.md` for evidence triage and root-cause workflow.
- `references/gdb-command-patterns.md` for breakpoints, watchpoints, conditional breakpoints, and stepping patterns.
- `references/common-native-bugs.md` for native failure signatures and likely causes.

## Evidence Report

Use this structure when reporting debugger findings:

```text
Failure:
- Signal/error:
- Reproduction command:
- GDB log:

Debugger evidence:
- Crashing frame:
- First relevant application frame:
- Suspicious variables:
- Thread state:

Root cause:
- What went wrong:
- Why it happened:

Fix:
- Files changed:
- Minimal change made:

Verification:
- Build result:
- Test result:
- GDB rerun result:
```

## Safety Rules

- Do not run destructive commands.
- Do not use `sudo`.
- Do not attach to arbitrary PIDs unless the user explicitly provides the PID or the process was launched by this session.
- Keep GDB logs and generated command files under `.debug/`.
- Prefer these wrapper scripts over interactive GDB.
- Bound stepping with `STEPS`; do not step hundreds of times blindly.
- Do not continue indefinitely on hangs.
- Do not delete core files or logs unless asked.

## Common Mistakes

- Guessing from source before reproducing under GDB.
- Only reading frame 0 when the root cause is in the caller.
- Ignoring other threads in a multithreaded crash or hang.
- Treating `<optimized out>` values as reliable.
- Confusing library frames with the first application-owned bad state.
- Applying broad defensive changes before identifying why the invalid state exists.
- Fixing symptoms without rerunning the original reproduction.
