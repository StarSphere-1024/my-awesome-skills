# MCU GDB Setup and Session

Use this reference to form a complete debug loop instead of issuing disconnected GDB commands.

## Identify the Session Matrix

Find or confirm these values:

- `ELF`: exact `.elf` file used by GDB, with symbols matching the flashed image.
- `GDB`: cross debugger, usually `arm-none-eabi-gdb`, `riscv-none-elf-gdb`, or a vendor-packaged GDB.
- `TARGET`: MCU, board, SoC, or QEMU machine.
- `PROBE`: CMSIS-DAP, ST-LINK, J-Link, Picoprobe, on-board debugger, or simulator.
- `GDBSERVER`: OpenOCD, pyOCD, J-Link GDB Server, ST-LINK_gdbserver, QEMU, or already-running server.
- `PORT`: commonly `:3333`, `:2331`, or `:61234`, but always prefer the backend log.
- `MODE`: `load` new firmware, attach to running firmware, or debug from reset.
- `REPRO`: the user action, test, peripheral event, packet, command, or boot path that triggers the fault.

If the ELF does not match the image on the device, PC-to-source mapping can be wrong. Rebuild and reload before trusting source lines.

## Build for Debugging

Prefer:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

For Make or custom builds, prefer equivalent flags:

```bash
CFLAGS="-g3 -O0" CXXFLAGS="-g3 -O0"
```

If the bug only reproduces under optimization, use debug information with the reproducing optimization level and mark optimized-out locals as unknown.

## Connect and Normalize Target State

Start GDB with the ELF:

```bash
arm-none-eabi-gdb build/firmware.elf
```

Inside GDB:

```gdb
set pagination off
set confirm off
target extended-remote :3333
monitor reset halt
info registers
```

Use `monitor help` after connecting. Monitor commands vary by backend; do not assume `reset halt` is supported verbatim.

## Load Versus Attach

Use `load` when GDB should program the image:

```gdb
monitor reset halt
load
monitor reset halt
break main
continue
```

Use attach-only when the target already contains the firmware or when loading would disturb state:

```gdb
monitor halt
info registers
bt
```

If attaching to a running RTOS target, halt first and inspect all thread-aware views the backend provides. If the backend lacks RTOS awareness, rely on CPU state, known task control blocks, and project-specific RTOS debug helpers.

## Breakpoint Strategy

Start narrow:

```gdb
break main
break HardFault_Handler
break assert_failed
break path/to/file.c:123
```

Use conditional breakpoints when the fault only occurs for a specific state:

```gdb
break driver.c:88 if len > sizeof(rx_buf)
commands
  silent
  bt 5
  info registers
  continue
end
```

Use watchpoints after identifying the address or variable that becomes invalid:

```gdb
watch global_state.error_code
watch *(unsigned int*)0x20001000
```

MCUs have few hardware watchpoints. Remove stale watchpoints before adding new ones.

## Inspect State

Use a small set repeatedly:

```gdb
info registers
info registers pc lr sp xpsr msp psp control
bt
frame 0
info args
info locals
x/16wx $sp
x/8i $pc-8
list *$pc
```

For peripheral or memory corruption bugs, inspect the producer and consumer. A faulting load/store often shows where bad state was consumed, not where it became bad.

## Close the Loop

Before editing, answer:

1. Which exact instruction or source line stopped?
2. Which value is invalid?
3. Which register, stack slot, memory address, or peripheral register proves it?
4. Which code path produced or allowed that value?
5. What is the smallest change that prevents the bad state?
6. Which rebuild, reload, reset, and reproduction will prove the fix?

After editing, repeat the same debug or test path. Verification should include rebuild output, reload/flash success, reset state, and the original trigger no longer producing the same fault.
