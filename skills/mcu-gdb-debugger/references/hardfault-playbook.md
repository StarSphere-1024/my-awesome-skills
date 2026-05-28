# Cortex-M HardFault Playbook

Use this reference when the target stops in `HardFault_Handler`, `MemManage_Handler`, `BusFault_Handler`, `UsageFault_Handler`, an assert/reset loop after a fault, or an RTOS fatal error path.

## First Read the Registers

Collect:

```gdb
info registers pc lr sp xpsr msp psp primask basepri faultmask control
x/wx 0xE000ED24
x/wx 0xE000ED28
x/wx 0xE000ED2C
x/wx 0xE000ED30
x/wx 0xE000ED34
x/wx 0xE000ED38
x/wx 0xE000ED3C
```

Addresses:

- `0xE000ED24` `SHCSR`
- `0xE000ED28` `CFSR`
- `0xE000ED2C` `HFSR`
- `0xE000ED30` `DFSR`
- `0xE000ED34` `MMFAR`
- `0xE000ED38` `BFAR`
- `0xE000ED3C` `AFSR`

Read `MMFAR` only as meaningful when `CFSR.MMARVALID` is set. Read `BFAR` only as meaningful when `CFSR.BFARVALID` is set.

## Recover the Exception Frame

On Cortex-M, exception entry stacks:

```text
sp[0] r0
sp[1] r1
sp[2] r2
sp[3] r3
sp[4] r12
sp[5] stacked_lr
sp[6] stacked_pc
sp[7] stacked_xpsr
```

If `lr` still contains an EXC_RETURN value:

- bit 2 set means the pre-fault stack was `PSP`
- bit 2 clear means the pre-fault stack was `MSP`
- common values: `0xFFFFFFF1`, `0xFFFFFFF9`, `0xFFFFFFFD`

GDB helper commands:

```gdb
set $fault_sp = (($lr & 4) ? $psp : $msp)
x/8wx $fault_sp
set $stacked_lr = ((unsigned int*)$fault_sp)[5]
set $stacked_pc = ((unsigned int*)$fault_sp)[6]
set $stacked_xpsr = ((unsigned int*)$fault_sp)[7]
p/x $stacked_lr
p/x $stacked_pc
p/x $stacked_xpsr
info line *$stacked_pc
x/8i $stacked_pc-8
```

If the current `lr` is not an EXC_RETURN value, the handler already called another function or the RTOS wrapped the fault. Inspect the handler prologue, saved fault context, or project fatal-error structure. Many RTOS ports pass the stacked frame pointer to a C fault handler; use that pointer instead of current `sp`.

If floating point is enabled and EXC_RETURN bit 4 is clear, an extended FP frame may be present. Account for the port's FP stacking layout before trusting offsets.

## Decode CFSR

`CFSR` combines MemManage, BusFault, and UsageFault status.

MemManage bits:

- bit 0 `IACCVIOL`: instruction fetch from an invalid/protected address.
- bit 1 `DACCVIOL`: data access violation.
- bit 3 `MUNSTKERR`: fault during exception return unstacking.
- bit 4 `MSTKERR`: fault during exception entry stacking.
- bit 5 `MLSPERR`: lazy FP state preservation fault.
- bit 7 `MMARVALID`: `MMFAR` contains a valid address.

BusFault bits:

- bit 8 `IBUSERR`: instruction bus error.
- bit 9 `PRECISERR`: precise data bus error; stacked PC is usually relevant.
- bit 10 `IMPRECISERR`: imprecise data bus error; fault may be after the bad store.
- bit 11 `UNSTKERR`: bus fault during exception return unstacking.
- bit 12 `STKERR`: bus fault during exception entry stacking.
- bit 13 `LSPERR`: lazy FP bus fault.
- bit 15 `BFARVALID`: `BFAR` contains a valid address.

UsageFault bits:

- bit 16 `UNDEFINSTR`: undefined instruction or bad code address.
- bit 17 `INVSTATE`: invalid EPSR/T-bit state, often bad function pointer or corrupted return.
- bit 18 `INVPC`: invalid exception return or corrupted EXC_RETURN.
- bit 19 `NOCP`: coprocessor/FPU instruction without enabled coprocessor.
- bit 24 `UNALIGNED`: unaligned access trapped.
- bit 25 `DIVBYZERO`: divide by zero trapped.

`HFSR.FORCED` means another configurable fault escalated to HardFault. Decode `CFSR`; do not stop at `HFSR`.

## Map Evidence to Likely Causes

- Stacked `pc` points into valid code and `CFSR.PRECISERR` with valid `BFAR`: inspect the load/store near stacked PC and the base/index register that formed `BFAR`.
- Stacked `pc` is `0x00000000`, `0xFFFFFFFF`, SRAM, or an odd implausible address: suspect bad function pointer, corrupted return address, stack overflow, vector table error, or invalid boot jump.
- `INVSTATE` or `INVPC`: inspect function pointers, callback tables, overwritten LR, hand-written assembly, bootloader handoff, and exception return path.
- `NOCP`: enable the FPU in startup/system init or compile without FP instructions for the target ABI.
- `UNALIGNED`: inspect packed structs, DMA buffers, protocol parsing, and casts from byte buffers to wider types.
- `DIVBYZERO`: inspect denominator provenance and whether divide-by-zero trapping is intentionally enabled.
- `STKERR`, `MSTKERR`, or `UNSTKERR`: suspect stack overflow, invalid process stack, bad RTOS task stack bounds, MPU guard region, or corrupted exception frame.
- `IMPRECISERR`: the stacked PC may be after the bad store. Use a watchpoint, enable stricter bus fault behavior if available, or inspect recent stores to peripheral/DMA/memory-mapped addresses.

## Fix and Verify

Prefer fixing the producer of invalid state:

- bad pointer or callback source
- missing bounds check before DMA or copy
- wrong linker script, vector table, bootloader offset, or stack size
- missing peripheral clock or invalid register sequence
- RTOS task stack too small or stack memory corrupted
- FPU/ABI mismatch

After a fix, rebuild, reload, reset, reproduce, and re-read fault registers if the target still stops. A new fault with different `CFSR` or stacked PC is a new investigation, not proof that the first diagnosis was wrong.
