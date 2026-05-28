---
name: mcu-gdb-debugger
description: Use for MCU firmware debugging with GDB/gdbserver, probe or QEMU targets, flash/attach flows, and Cortex-M fault analysis.
---

# MCU GDB Debugger

Use debugger evidence to close the embedded firmware debug loop: identify the exact target setup, connect through the correct gdbserver, halt/load/attach, reproduce, inspect CPU and fault state, make the smallest code change, rebuild, reflash, and verify on the same reproduction.

## Scope

Use for MCU firmware running on bare metal, RTOS, QEMU, or probe-connected boards where the key artifact is an ELF file and the debug path is GDB plus a gdbserver backend.

## Debug Contract

Before editing firmware, collect or infer:

1. ELF path and whether it has symbols.
2. MCU or board, core family, and memory map if known.
3. Probe/interface: CMSIS-DAP, ST-LINK, J-Link, Picoprobe, on-board debug, QEMU, or another backend.
4. gdbserver backend and port: OpenOCD, pyOCD, J-Link GDB Server, ST-LINK_gdbserver, QEMU `-gdb`, vendor IDE server, or an already-running server.
5. Session mode: flash/load a new image, attach to existing firmware, or connect to a simulated paused target.
6. Reproduction trigger and expected stop condition: breakpoint, fault handler, assert, reset loop, hang, bad peripheral state, or wrong output.

If any of ELF, target, probe, or backend is unknown, inspect the repo build files, board configs, launch configs, README, CI scripts, or user-provided command history before guessing.

## Workflow

1. Build a debuggable ELF. Prefer debug symbols and avoid stripping. If optimization is needed to reproduce, keep symbols and record that values may be optimized out.
2. Start or locate the gdbserver backend. See `references/backend-patterns.md` for backend-specific command patterns.
3. Start the matching cross GDB, usually `arm-none-eabi-gdb <firmware.elf>`.
4. Connect with `target extended-remote` or `target remote`, then confirm the target halted state.
5. Run `monitor reset halt` or the backend equivalent before loading or inspecting early boot state.
6. Use `load` for flash/RAM download sessions, or skip `load` when attaching to existing firmware.
7. Set focused breakpoints or watchpoints. Prefer `main`, fault handlers, assert handlers, suspicious source locations, and producer locations for bad state.
8. Continue or step only as far as needed. Read registers, backtrace, source, disassembly, and memory around the suspicious state.
9. For HardFault or configurable faults, read SCB fault registers and the stacked exception frame before changing code. See `references/hardfault-playbook.md`.
10. Make the smallest source or configuration fix that explains the collected evidence.
11. Rebuild, reflash or reload, reset, reproduce, and verify the original failure is gone.

## Minimal GDB Skeleton

Adapt this sequence to the backend and target:

```gdb
set pagination off
set confirm off
file build/firmware.elf
target extended-remote :3333
monitor reset halt
load
monitor reset halt
break main
continue
```

For attach-only sessions:

```gdb
file build/firmware.elf
target remote :3333
monitor halt
info registers
bt
```

## Evidence Standard

For every stop, record:

- stop reason and current frame
- `pc`, `lr`, `sp`, `xpsr`, plus `msp`, `psp`, and `control` on Cortex-M
- `bt` and the first application-owned frame
- source line and disassembly around `pc`
- relevant arguments, locals, global state, peripheral registers, and memory bytes/words
- for faults: `CFSR`, `HFSR`, `BFAR`, `MMFAR`, active stack pointer, and stacked `pc/lr/xpsr`

Do not treat "the board resets less often" or "GDB no longer stops immediately" as sufficient verification. Re-run the same trigger after rebuild and reload.

## References

Load only what is needed:

- `references/setup-and-session.md` for the end-to-end MCU debug loop and safety checks.
- `references/backend-patterns.md` for OpenOCD, pyOCD, J-Link, ST-LINK, QEMU, and generic gdbserver command patterns.
- `references/hardfault-playbook.md` for Cortex-M fault registers, exception frame recovery, and mapping PC/LR/SP/xPSR/CFSR/HFSR/BFAR/MMFAR to likely root causes.

## Safety

- Do not mass erase, unlock readout protection, change option bytes, or alter fuse/security settings unless the user explicitly asks.
- Prefer halt/load/reset over vendor GUI automation when working from a terminal.
- Keep debug transcripts, GDB command files, and backend logs under `.debug/` when creating files.
- Do not leave an unbounded `continue` or step loop running without a breakpoint, timeout, or visible stop condition.
- Avoid writing arbitrary memory or peripheral registers unless the value, address, and hardware effect are understood.
