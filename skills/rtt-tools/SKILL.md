---
name: rtt-tools
description: Use when debugging embedded firmware through SEGGER J-Link RTT - capture RTT output, send RTT console commands, or open an interactive RTT console.
---

# RTT Tools

Use `scripts/rtt.py` for SEGGER J-Link RTT.

RTT is RTOS-independent. Do not assume Zephyr unless the project clearly uses Zephyr/NCS.

## Requirements

Firmware must:

- include SEGGER RTT support
- expose an RTT control block
- configure an up-buffer for target output
- configure and consume a down-buffer if input is needed
- route its shell/console/log backend to RTT if shell/log access is expected

## Setup

```bash
RTT=/path/to/skills/rtt-tools/scripts/rtt.py
```

Defaults:

```text
Interface: SWD
Speed: 4000
GDB port: 2331
RTT port: 19021
```

Use `--dev-id <serial>` when multiple J-Links are connected.

## Commands

Run one command:

```bash
python "$RTT" command -d <device> "help"
```

The tool suppresses J-Link startup noise by default. Use `--verbose` only when
diagnosing the J-Link server itself.

Open console:

```bash
python "$RTT" console -d <device>
```

Capture reset logs:

```bash
python "$RTT" capture -d <device> --reset --seconds 10
```

Attach to an existing RTT server:

```bash
python "$RTT" command --attach "help"
```

Useful options:

```text
--timeout <seconds>    command timeout
--seconds <seconds>    capture duration
--gdb <path>           explicit GDB path
--no-drain             keep old RTT buffered data
--no-strip-ansi        keep ANSI escapes in command output
--verbose              show JLinkGDBServer startup output
```

## Procedure

1. Build and flash with the project’s normal workflow.
2. Use `capture --reset` for boot logs.
3. Use `command` for automated shell checks.
4. Use `console` only for human interaction.
5. Stop this tool before starting another tool that needs the same J-Link or ports.

## Zephyr / NCS Notes

Only apply this section to Zephyr/NCS projects.

Shell over RTT usually needs:

```text
CONFIG_USE_SEGGER_RTT=y
CONFIG_SHELL=y
CONFIG_SHELL_BACKEND_RTT=y
```

Logging over RTT usually needs:

```text
CONFIG_LOG=y
CONFIG_LOG_BACKEND_RTT=y
```

If shell and logging share channel 0, check for RTT channel/buffer conflicts.

Example for nRF54L15:

```bash
python "$RTT" capture -d NRF54L15_M33 --reset --seconds 10
python "$RTT" command -d NRF54L15_M33 "help"
python "$RTT" console -d NRF54L15_M33
```

## Troubleshooting

No output:

* check J-Link visibility
* check device name
* check flashed image is running
* check firmware initializes RTT
* check RTT up-buffer exists

Command has no response:

* first confirm output works
* check RTT down-buffer exists
* check shell reads from RTT
* try a simple known command: `help`, `version`, or `status`

Missing early logs:

```bash
python "$RTT" capture -d <device> --reset --seconds 10
```

Old logs before new boot logs:

* keep default drain behavior
* avoid `--no-drain`

Port conflict:

* stop other J-Link/RTT tools
* or use `--attach`

GDB not found:

```bash
python "$RTT" capture -d <device> --reset --gdb /path/to/gdb --seconds 10
```

## Reporting

Report:

* command used
* reset or attach mode
* relevant output
* whether RTT output worked
* whether RTT input worked

```
