# Embedded Systems Development Rules

## Architecture & Design

- **PRIORITIZE platform-agnostic logic**: Core business logic (algorithms, FSMs) MUST be portable—no direct dependencies on platform-specific headers or APIs.
- **MANDATE Hardware Abstraction Layer (HAL)**: Application logic MUST NOT directly access registers. Route all hardware operations through HAL interfaces.
- **REQUIRE modularity**: Each module handles single responsibility with high cohesion, low coupling.
- **MANDATE Finite State Machines (FSM)**: Use FSMs for complex control logic (button debouncing, protocol parsing, menu navigation).
- **PRIORITIZE event-driven designs**: Prefer interrupts + event queues over polling loops.
- **FORBID blocking patterns in interruptible contexts**: No `delay()`, `HAL_Delay()`, or spin-loops in main execution paths.

## Memory Management

- **FORBID dynamic memory allocation**: No `malloc/free` or `new/delete` in production firmware.
- **MANDATE static allocation**: Use global/static variables or memory pools.
- **REQUIRE stack monitoring**: Use `uxTaskGetStackHighWaterMark()` to verify task stack allocation.
- **AVOID `String` objects on AVR/ESP32**: Use C-style strings (char arrays) to prevent heap fragmentation.
- **USE `F()` macro on Arduino**: Store constant strings in Flash: `Serial.println(F("text"))`.

## Real-Time Behavior

- **FORBID blocking calls in main loop**: Replace `delay()` with `millis()`-based timing or hardware timers.
- **MANDATE non-blocking I/O**: Use DMA for ADC, SPI, UART data transfers.
- **REQUIRE event-driven networking**: Wi-Fi/BT operations MUST use event handlers, not polling.
- **IMPLEMENT connection auto-recovery**: Network disconnections MUST trigger automatic reconnection attempts.

## Interrupt (ISR) Discipline

- **KEEP ISRs minimal**: ISRs MUST execute in microseconds, not milliseconds.
- **FORBID blocking operations in ISRs**: No delays, no waiting on flags, no complex computation.
- **FORBID standard library calls in ISRs**: No `printf`, `malloc`, or non-reentrant functions.
- **OFFLOAD processing to main context**: ISRs set flags/semaphores; main loop or tasks handle data processing.
- **PROTECT shared data with critical sections**: Disable interrupts when main code accesses ISR-shared variables.

## FreeRTOS Correctness

- **REQUIRE one-task-one-responsibility**: Each task handles single functional area.
- **FORBID task exit**: Tasks MUST be infinite loops; use `vTaskDelete()` for termination.
- **USE `vTaskDelayUntil()` for periodic tasks**: Compensates for execution time jitter.
- **MANDATE thread-safe communication**: Use Queues, Semaphores, Mutexes—NEVER share global variables between tasks.
- **USE Mutexes with priority inheritance**: Prevents priority inversion on shared resources.
- **USE binary semaphores for ISR-to-task sync**: ISR gives semaphore, task blocks waiting.
- **ENABLE `configASSERT`**: Catch API misuse during development immediately.
- **ENABLE stack overflow detection**: Set `configCHECK_FOR_STACK_OVERFLOW = 2`.
- **FORBID `while(1)` without `vTaskDelay()`**: Tasks MUST yield CPU to prevent watchdog reset.

## Toolchain & Build Hygiene

- **MANDATE CMake or modern build systems**: Avoid write Makefiles manualy; use CMake, ESP-IDF, PlatformIO.
- **REQUIRE strict compiler flags**: `-Wall -Wextra -Werror -pedantic`.
- **REQUIRE reproducible builds**: Use Docker/DevContainers for toolchain consistency.
- **VERSION hardware dependencies**: Track PCB version, schematic, pin mapping alongside firmware.
- **ENABLE static analysis**: Run Cppcheck, SonarQube, or PC-lint in CI.
- **MONITOR resource usage**: Track Flash/RAM usage per build; fail CI if thresholds exceeded.

## Testing Strategy

- **MANDATE dual-target testing**:
  - Host (PC): Unit test business logic with mocks (Unity, CMock, Google Test).
  - Target (MCU): Test hardware drivers and timing on real device.
- **IMPLEMENT Hardware-in-the-Loop (HIL)**: Automate sensor simulation and output capture.
- **USE simulators when hardware unavailable**: QEMU, Renode for early integration testing.
- **REQUIRE code coverage**: Host tests MUST generate coverage reports (gcov/lcov).

## Reliability & Safety

- **MANDATE watchdog timers**: Enable IWDG/WWDG; feed in main loop or lowest-priority task.
- **FORBID feeding watchdog in ISR**: Feed only after successful main task completion.
- **USE assertions liberally**: `assert()` for sanity checks in development.
- **IMPLEMENT HardFault handlers**: Capture stack trace, PC, registers to Flash/EEPROM for post-mortem.
- **REQUIRE secure boot**: Verify firmware signature before execution.
- **IMPLEMENT A/B partition updates**: Support rollback on OTA failure.
- **USE wear-leveling for Flash**: LittleFS/FatFS for frequent data writes.
- **ENCRYPT sensitive data**: Use hardware security modules (TrustZone, HSM) when available.
- **VALIDATE all external inputs**: Check bounds, ranges, checksums on sensor/communication data.

## Platform-Specific Rules

### Arduino

- **FORBID long `delay()` calls**: Use `millis()` for all timing.
- **MANDATE `F()` macro for strings**: Prevent SRAM exhaustion.
- **AVOID `String` class**: Use char arrays to prevent heap fragmentation.
- **REQUIRE custom functions**: Extract logic from `loop()` into named functions.
- **USE multi-file structure**: Move complex logic to `.cpp/.h` library files.
- **LOCK library versions**: Document exact library versions for reproducibility.

### STM32

- **USE STM32CubeMX/CubeIDE**: Generate initialization code; place app code in `USER CODE BEGIN/END` blocks.
- **CHOOSE HAL vs LL appropriately**:
  - HAL: Complex peripherals (USB, Ethernet), rapid prototyping.
  - LL: Performance-critical paths (high-speed ADC, tight loops).
- **PRIORITIZE DMA**: Use for all bulk transfers (ADC, SPI, UART).
- **CHECK HAL return values**: Handle `HAL_ERROR`, `HAL_BUSY`, `HAL_TIMEOUT`.
- **ENABLE both IWDG and WWDG**: For production safety-critical systems.

### ESP32

- **MANDATE FreeRTOS tasks**: Separate Wi-Fi, sensors, web server into distinct tasks.
- **USE event-driven Wi-Fi handling**: Register event handlers; no polling connection status.
- **IMPLEMENT auto-reconnect logic**: Handle Wi-Fi drops gracefully.
- **SELECT appropriate sleep mode**:
  - Modem-sleep: Short idle periods.
  - Light-sleep: GPIO wake sources.
  - Deep-sleep: Battery-powered periodic sampling.
- **DISABLE unused peripherals before sleep**: Power down Wi-Fi, BT, peripherals.
- **MANAGE partition table**: Configure for OTA when needed.

## Debugging

- **USE SEGGER RTT for development**: Faster than UART, minimal real-time impact.
- **IMPLEMENT log levels**: DEBUG, INFO, WARN, ERROR with compile-time filtering.
- **DISABLE debug logs in production**: Reduce overhead and information leakage.

---

## Domain Constraints (Injection Template)

<domain_constraints>
**MEMORY**: FORBID malloc/free/new/delete. MANDATE static allocation or memory pools.
**REAL-TIME**: FORBID delay()/HAL_Delay in main paths. MANDATE non-blocking, event-driven designs.
**ISR**: ISRs MUST be minimal, fast, non-blocking. FORBID printf/malloc in ISRs. Offload processing.
**FREERTOS**: MANDATE Queues/Semaphores/Mutexes for task communication. FORBID shared globals. ENABLE configASSERT. FORBID while(1) without vTaskDelay().
**WATCHDOG**: MANDATE IWDG/WWDG. Feed in main loop, NEVER in ISR.
**BUILD**: REQUIRE -Wall -Wextra -Werror. MANDATE CMake/modern build. USE Docker for reproducibility.
**TESTING**: MANDATE dual-target (Host PC mocks + Target MCU). REQUIRE coverage reports.
**SAFETY**: MANDATE assertions, HardFault handlers, input validation.
**ARDUINO**: USE F() macro, millis(), avoid String class.
**STM32**: PRIORITIZE DMA, check HAL returns, use HAL/LL appropriately.
**ESP32**: PREFER ESP-IDF for production; MANDATE FreeRTOS tasks, event-driven Wi-Fi, manage power modes.
</domain_constraints>
