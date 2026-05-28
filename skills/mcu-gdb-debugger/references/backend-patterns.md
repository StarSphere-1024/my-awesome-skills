# MCU GDB Server Backend Patterns

Use these as starting points. Prefer commands already present in the repo, board docs, launch configs, or CI scripts.

## OpenOCD

Typical launch:

```bash
openocd -f interface/cmsis-dap.cfg -f target/stm32f4x.cfg
openocd -f interface/stlink.cfg -f target/stm32g0x.cfg
openocd -f interface/jlink.cfg -f target/nrf52.cfg
```

GDB:

```gdb
target extended-remote :3333
monitor reset halt
load
monitor reset halt
```

Useful checks:

```gdb
monitor targets
monitor poll
monitor mdw 0xE000ED00 4
```

If connection fails, check adapter speed, SWD versus JTAG, target voltage, reset wiring, and exact target config.

## pyOCD

Typical launch:

```bash
pyocd gdbserver --target <target-name> --frequency 4000000
pyocd list --targets
pyocd list --probes
```

GDB:

```gdb
target remote :3333
monitor reset halt
load
monitor reset halt
```

Use pyOCD when CMSIS-DAP support, target packs, or Python-based board scripts are already part of the project.

## J-Link GDB Server

Typical launch:

```bash
JLinkGDBServerCLExe -device <device> -if SWD -speed 4000 -port 2331
```

GDB:

```gdb
target remote :2331
monitor reset
monitor halt
load
monitor reset
```

Device names must match J-Link's database. If flash download fails, confirm the device, interface, endian mode, flash loader support, and whether external flash needs a project-specific loader.

## ST-LINK GDB Server

Typical launch:

```bash
ST-LINK_gdbserver -p 61234
```

GDB:

```gdb
target remote :61234
monitor reset
load
monitor reset
```

Vendor server options vary by STM32CubeIDE and package version. Prefer the command captured from an existing launch configuration.

## QEMU MCU Targets

Typical launch:

```bash
qemu-system-arm -M <machine> -cpu <cpu> -kernel build/firmware.elf -S -gdb tcp::3333
```

GDB:

```gdb
target remote :3333
monitor system_reset
break main
continue
```

QEMU often models CPU behavior better than board peripherals. Treat peripheral results as model-dependent unless the QEMU machine explicitly supports that device.

## Already-Running gdbserver

If the user provides a port or backend log:

```gdb
file build/firmware.elf
target remote :<port>
monitor help
info registers
```

Do not start a second server on the same probe unless the first one is stopped. Probe drivers usually allow only one active client.

## Connection Failure Triage

- Cannot open probe: another IDE/server owns it, permissions issue, bad USB path, or missing driver.
- Cannot halt target: wrong interface, speed too high, target held in reset, low power mode, watchdog reset loop, or locked debug.
- Cannot load flash: wrong chip config, protected flash, missing flash loader, external flash not configured, or ELF sections outside writable memory.
- Breakpoints do not bind: ELF mismatch, optimized/inlined code, flash hardware breakpoint limit, or wrong source path mapping.
- PC is implausible after reset: wrong vector table, wrong image base, bootloader offset mismatch, stack overflow, or attach to stale firmware.
