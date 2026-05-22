# GDB Command Patterns

Use these patterns when the first GDB log is not enough to locate when a value becomes invalid.

## Breakpoints

```gdb
break function_name
break path/to/file.c:123
run
info args
info locals
bt
```

Use source-location breakpoints when function names are overloaded or inlined.

## Conditional Breakpoints

```gdb
break parser.c:88 if len > capacity
break worker.cpp:212 if ptr == 0
commands 1
  silent
  bt 5
  info args
  info locals
  continue
end
commands 2
  silent
  bt 5
  info args
  info locals
  continue
end
```

Use conditional breakpoints when the bug only appears for a specific size, state, thread, or pointer value.
Use `commands <breakpoint-number>` when multiple breakpoints exist; plain `commands` binds to the most recently created breakpoint.

## Watchpoints

```gdb
watch global_or_local_variable
watch *ptr
rwatch *ptr
awatch *ptr
```

Use watchpoints after you know the address or variable that becomes corrupted. Prefer hardware watchpoints when available. Watchpoints can slow execution and may be limited in number.
For `watch *ptr`, `rwatch *ptr`, and `awatch *ptr`, first stop in a frame where `ptr` is initialized and in scope.

## Bounded Stepping

Start with `next`. Use `step` only to enter a suspicious function.

```bash
BREAK=path/file.c:123 STEPS=40 MODE=next scripts/gdb-step.sh ./program arg1
BREAK=suspicious_function STEPS=30 MODE=step scripts/gdb-step.sh ./program arg1
```

Stop stepping when the bad state is visible. Do not convert debugging into an unbounded trace.

## Optimized Code

If GDB shows `<optimized out>`, do not treat the value as known. Rebuild with `-g -O0` or `RelWithDebInfo` when optimization is required to reproduce.

## Forks and Execs

Only use these when the failure involves child processes:

```gdb
set follow-fork-mode child
set detach-on-fork off
catch exec
```

Keep the GDB run bounded and log the reason these settings were needed.
