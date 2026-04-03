---
name: rtt-tools
description: Use when debugging Zephyr RTOS firmware with J-Link RTT, when UART is unavailable, when needing to read RTT logs, send Shell commands, or manage J-Link processes
---

# J-Link RTT Tools

## Overview

A complete toolset for interacting with SEGGER J-Link RTT (Real-Time Transfer) streams. Solves the infinite stream problem and automates the debugging workflow.

**Core insight:** RTT is an infinite continuous stream - never use blocking commands like `nc` or `telnet` directly, they will hang forever.

## Tool Suite

| Tool | Purpose |
|------|---------|
| `rtt_reader.py` | Read RTT logs, send Shell commands |
| `rtt_clean.py` | Kill occupied J-Link processes |
| `rtt_start.py` | One-key full workflow automation |
| `rtt_stop.py` | Stop background JLinkGDBServer |

## Quick Reference

### rtt_reader.py - Read Logs

```bash
python rtt_reader.py                         # Read 3s of logs (ANSI stripped by default)
python rtt_reader.py -t 5                    # Read 5s of logs
python rtt_reader.py -c "help"               # Send command, read response
python rtt_reader.py -c "sys reboot" -t 2    # Reboot, capture output
python rtt_reader.py --no-strip-ansi         # Keep ANSI color codes
python rtt_reader.py -c "log level 3" --no-strip-ansi  # Keep colors
python rtt_reader.py -c "help" --wait-for-shell -t 5   # Wait for shell prompt first
```

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --timeout` | 3 | Seconds to listen for RTT output |
| `-c, --command` | - | Zephyr Shell command to send before reading |
| `--no-strip-ansi` | false | Keep ANSI color codes (default: stripped) |
| `--wait-for-shell` | false | Wait for "rtt:~$" prompt before sending command |
| `--shell-timeout` | 10 | Timeout for shell prompt detection in seconds |
| `--host` | 127.0.0.1 | RTT server hostname |
| `--port` | 19021 | RTT server port |

### rtt_clean.py - Kill Occupied Processes

```bash
python rtt_clean.py              # List and kill all J-Link processes
python rtt_clean.py --list       # Only list, don't kill
python rtt_clean.py --force      # Use kill -9 for stubborn processes
python rtt_clean.py --yes        # Skip confirmation prompt
python rtt_clean.py --pid 12345  # Kill specific PID only
```

| Option | Description |
|--------|-------------|
| `--list, -l` | Only list processes, don't kill |
| `--force, -f` | Use SIGKILL instead of SIGTERM |
| `--pid, -p` | Kill specific PID only |
| `--yes, -y` | Skip confirmation prompt |

### rtt_start.py - One-Key Workflow

**Note:** `--device` is REQUIRED. No default value is provided for project-specific settings.

```bash
python rtt_start.py -d nRF52840_XXAA                 # Minimal: just device
python rtt_start.py -d nRF52840_XXAA --keep-alive    # Start GDB server in background
python rtt_start.py -d nRF52840_XXAA --flash --elf build/zephyr/zephyr.elf
python rtt_start.py -d nRF52840_XXAA --no-reset
python rtt_start.py -d nRF52840_XXAA --timeout 5     # Read RTT for 5 seconds

# Note: ANSI codes are stripped by DEFAULT. Use --no-strip-ansi to keep them.
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--device, -d` | **Yes** | - | Target device (e.g., nRF52840_XXAA) |
| `--speed` | No | 4000 | J-Link speed in kHz |
| `--interface, -i` | No | SWD | SWD or JTAG |
| `--elf` | No\* | - | ELF file to flash (\*required with --flash) |
| `--flash` | No | false | Flash target before reading RTT |
| `--no-reset` | No | false | Skip target reset |
| `--timeout, -t` | No | 3 | RTT read timeout in seconds |
| `--no-strip-ansi` | No | false | Keep ANSI color codes (default: stripped) |
| `--keep-alive` | No | false | Start JLinkGDBServer in background and exit |
| `--pid-file-dir` | No | ~/.rtt_tools | Directory for PID file |

### rtt_stop.py - Stop Background Server

```bash
python rtt_stop.py                       # Stop using default PID file location
python rtt_stop.py --pid-file-dir /custom  # Use custom PID file directory
```

| Option | Description |
|--------|-------------|
| `--pid-file-dir` | Directory containing PID file (default: ~/.rtt_tools) |

**Note:** This command only works when JLinkGDBServer was started with `rtt_start.py --keep-alive`.

## Configuration File

**Optional:** `rtt_start.py` no longer reads config files. All settings must be passed via CLI.

If you want to avoid typing common options, create a shell alias in your `.bashrc`:

```bash
alias rtt-start='python rtt_start.py -d nRF52840_XXAA --elf build/zephyr/zephyr.elf'
```

## How It Works

### rtt_reader.py Flow

```
1. Connect to TCP 19021 (J-Link RTT telnet port)
2. If --wait-for-shell: wait for "rtt:~$" prompt (up to --shell-timeout seconds)
3. If command provided: send with newline, wait 0.2s
4. Non-blocking read loop with timeout
5. Strip ANSI codes if requested
6. Gracefully exit and return captured output
```

### rtt_start.py Workflow

```
1. Kill existing J-Link processes (rtt_clean)
2. Start JLinkGDBServer in background
3. Flash ELF file (if --flash specified)
4. Reset target (unless --no-reset)
5. Read RTT output with clean formatting

With --keep-alive:
1-2. Same as above
3. Write PID to ~/.rtt_tools/gdb_server.pid
4. Exit immediately (server keeps running)
```

### rtt_stop.py Flow

```
1. Read PID from ~/.rtt_tools/gdb_server.pid
2. Send SIGTERM to process
3. Wait up to 5s for graceful exit
4. If still running, send SIGKILL
5. Remove PID file
```

## Error Handling

| Error | Tool Returns |
|-------|--------------|
| Connection refused | "J-Link RTT server is not running on port 19021..." |
| Connection timeout | "Connection to host:port timed out after Xs" |
| UTF-8 decode errors | Replaced with `` (uses `errors='replace'`) |
| No J-Link processes | "No J-Link processes found." |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `nc 127.0.0.1 19021` directly | Will hang forever - use rtt_reader.py |
| Using `telnet 127.0.0.1 19021` | Will hang forever - use rtt_reader.py |
| J-Link port occupied | Run `rtt_clean.py --yes` first |
| ANSI colors in output | Default is stripped; use `--no-strip-ansi` to keep |
| RTT control block not found | Ensure firmware is running, not halted |
| Too short timeout | Increase `-t` if device is slow to respond |
| Commands not responding | Use `--wait-for-shell` to wait for shell ready |
| Can't send multiple commands | Use `rtt_start.py --keep-alive` + `rtt_stop.py` |

## Typical Workflows

### Quick Log Check
```bash
# Just read current logs (ANSI stripped by default)
python rtt_reader.py -t 2
```

### Send Command and See Response
```bash
# Check kernel threads
python rtt_reader.py -c "kernel threads" -t 2

# Check memory usage
python rtt_reader.py -c "log app_memory" -t 2

# Wait for shell to be ready before sending command
python rtt_reader.py -c "help" --wait-for-shell -t 5
```

### Continuous Debugging Session (Multiple Commands)
```bash
# 1. Start GDB server in background
python rtt_start.py -d NRF54L15_M33 --keep-alive

# 2. Send multiple commands without restarting server
python rtt_reader.py -c "help" --wait-for-shell -t 3
python rtt_reader.py -c "i2c scan i2c21" -t 5
python rtt_reader.py -c "log level 3" -t 3

# 3. Stop background server when done
python rtt_stop.py
```

### Full Debug Session
```bash
# 1. Clean up any stuck processes
python rtt_clean.py --yes

# 2. Start everything and read initial logs
python rtt_start.py --flash --elf build/zephyr/zephyr.elf

# 3. Continue monitoring
while true; do python rtt_reader.py -t 2; done
```

### Troubleshooting
```bash
# J-Link seems stuck - kill and restart
python rtt_clean.py --force --yes
python rtt_start.py --no-flash
```

## Prerequisites

- J-Link software installed (JLinkExe, JLinkGDBServer, JLinkFlash)
- RTT enabled in Zephyr config (`CONFIG_SEGGER_RTT=y`)
- For rtt_clean.py: `pgrep` command (standard on Linux)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Connection failure or operation failed |
