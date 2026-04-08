---
name: rtt-tools
description: Use when debugging Zephyr RTOS firmware with J-Link RTT
---

# J-Link RTT Tools

## When to Trigger

Use this skill when the user needs to:
- Debug Zephyr RTOS firmware using J-Link RTT
- Read RTT logs when UART is unavailable
- Send shell commands to the target device
- Manage J-Link GDB server processes

**Architecture:** The RTT daemon captures logs while the server exposes port 19021; always start `server` → `daemon` → flash/reset so early boot RTT output reaches the daemon before you read/send.

## Quick Reference

```bash
# Start JLinkGDBServer
python rtt.py server start -d nRF52840_XXAA
# Start daemon for continuous logging (required for `send`)
python rtt.py daemon start
# Flash/reset target after daemon is ready
# west flash
# Read or send via daemon
python rtt.py read --lines 50
python rtt.py send "help" --wait-for-shell
# Stop when done
python rtt.py daemon stop
python rtt.py server stop
```

## Important Notes

| Note | Explanation |
|------|-------------|
| Daemon required | `send` requires daemon to be running (communicates via Unix Socket) |
| Continuous logging | Daemon continuously captures RTT output - no stream truncation |
| Startup order matters | Start `server` → `daemon` → flash/reset so no boot RTT is lost |
| Command forwarding | `send` forwards commands to daemon, which relays them over RTT |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `send` without daemon running | Start daemon first: `python rtt.py daemon start` |
| Flashing before daemon is running | Use this order: `python rtt.py server start` -> `python rtt.py daemon start` -> flash/reset target |
| Using `nc 127.0.0.1 19021` directly | Will hang forever — use `rtt.py send` |
| Commands not responding | Use `--wait-for-shell` to wait for shell ready |
| ANSI colors in output | Default is stripped; use `--no-strip-ansi` to keep |

## Prerequisites

- J-Link software installed (JLinkGDBServer)
- RTT enabled in Zephyr config (`CONFIG_SEGGER_RTT=y`)

## References

- `references/` directory for additional documentation
