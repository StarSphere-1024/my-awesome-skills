# GDB Diagnosis Playbook

Use this reference after collecting a GDB log. The goal is to find the first bad application-owned state, not merely the frame where the process stopped.

## Crash Triage

1. Confirm the signal or stop reason from `info program`.
2. Read `thread apply all bt full`; identify the crashing thread.
3. Walk from frame 0 upward until the first application-owned frame appears.
4. Inspect `info args` and `info locals` in that frame and its caller.
5. Classify the invalid state:
   - null or invalid pointer
   - wrong length or index
   - unexpected enum or state
   - lifetime or ownership violation
   - corrupted structure fields
   - assertion precondition failure
6. Ask when that state became invalid. If the GDB log only shows where it was consumed, use a breakpoint, conditional breakpoint, or watchpoint on the producer.

## Hang Triage

Compare two or more `gdb-hang.sh` snapshots.

- Same top frame and locals advancing: likely slow work or tight loop.
- Same top frame and locals unchanged: likely infinite loop or blocked wait.
- Threads waiting on mutexes, condition variables, futexes, joins, or locks: inspect owner/waiter relationships.
- All worker threads idle while one coordinator waits: inspect queue, wakeup, shutdown, or notification logic.

## Root-Cause Standard

Before editing code, answer:

1. What exactly failed?
2. Where did execution stop?
3. Which frame is the first relevant application frame?
4. Which value is invalid?
5. Which code path produced or allowed that value?
6. Why did existing checks not prevent it?
7. What is the smallest fix?
8. How will the same reproduction prove the fix?

## Minimal Fix Guidance

Prefer correcting the producer of invalid state. Add a defensive check only when invalid input is a valid external condition or when preserving API boundaries requires it.

Avoid broad rewrites while the failure is active. Change the narrowest code path that explains the collected evidence, then rerun the same reproduction.
