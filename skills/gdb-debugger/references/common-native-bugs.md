# Common Native Bug Signatures

Use this reference to map debugger evidence to likely root causes. Treat these as hypotheses that must match GDB evidence.

## Null Pointer

Signals:

- crash at address `0x0` or near zero
- argument or local pointer is `0x0`
- crash occurs on dereference, member access, or virtual call

Fix the missing initialization, failed allocation handling, optional-value contract, or caller precondition. Do not add a null check unless null is a legitimate input.

## Dangling Pointer or Use After Free

Signals:

- pointer value is non-null but points to freed or implausible memory
- crash occurs after ownership transfer, container reallocation, or destructor/free path
- object fields contain poison or inconsistent values

Find the lifetime transition. Prefer ownership correction over a late validity check.

## Out-of-Bounds Access

Signals:

- index equals or exceeds length
- pointer arithmetic steps past buffer bounds
- crash depends on input length or boundary cases

Fix bounds calculation at the producer. Verify with the smallest input that reproduces the boundary.

## Stack Corruption

Signals:

- backtrace contains corrupt frames or impossible return addresses
- local arrays or unsafe copies near the crash
- crash appears after returning from a function

Inspect writes before the corrupted return path. Look for unchecked copy, format, or length logic.

## Heap Corruption

Signals:

- crash in allocator/free implementation
- double free, invalid free, or corrupted heap metadata
- application frame before allocator call owns a pointer or size mismatch

Do not stop at allocator frame 0. Inspect the application caller and the allocation/free ownership history.

## Deadlock

Signals:

- multiple threads blocked in mutex, futex, condition variable, join, or lock code
- no frame changes across snapshots
- lock acquisition order differs across threads

Identify the lock each thread owns and waits for. Fix lock ordering, missing unlock, missed notify, or shutdown sequencing.

## Infinite Loop

Signals:

- same application frame across snapshots
- loop counters or cursor variables do not advance
- CPU usage remains high

Inspect loop exit conditions and state updates. Fix the transition that should make progress.
