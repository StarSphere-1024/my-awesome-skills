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

**Architecture:** RTT daemon continuously captures RTT output and writes to log files. The `send` command communicates with the daemon via Unix Socket to send commands, ensuring no RTT stream is missed.

## Quick Reference

```bash
# Start JLinkGDBServer (provides RTT on port 19021)
python rtt.py server start -d nRF52840_XXAA

# Start daemon for continuous logging (REQUIRED for send)
python rtt.py daemon start

# Read logs
python rtt.py read --lines 50
python rtt.py read --grep "ERROR"

# Send commands (via daemon Unix Socket)
python rtt.py send "help" --wait-for-shell
python rtt.py send "kernel threads" -n 30

# Stop when done
python rtt.py daemon stop
python rtt.py server stop
```

## Typical Workflow

```bash
# 1. Start JLinkGDBServer
python rtt.py server start -d nRF52840_XXAA

# 2. Start daemon for continuous logging
python rtt.py daemon start

# 3. Debug (view logs, send commands)
python rtt.py read --lines 50
python rtt.py send "kernel threads" --wait-for-shell -n 30

# 4. Stop when done
python rtt.py daemon stop
python rtt.py server stop
```

## Important Notes

| Note | Explanation |
|------|-------------|
| Daemon required | `send` requires daemon to be running (communicates via Unix Socket) |
| Continuous logging | Daemon continuously captures RTT output - no stream truncation |
| Command forwarding | `send` forwards commands to daemon, which sends via RTT and logs response |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `send` without daemon running | Start daemon first: `python rtt.py daemon start` |
| Using `nc 127.0.0.1 19021` directly | Will hang forever — use `rtt.py send` |
| Commands not responding | Use `--wait-for-shell` to wait for shell ready |
| ANSI colors in output | Default is stripped; use `--no-strip-ansi` to keep |

## Prerequisites

- J-Link software installed (JLinkGDBServer)
- RTT enabled in Zephyr config (`CONFIG_SEGGER_RTT=y`)

## Testing

```bash
pytest tests/ -v
```

Tests are skipped if RTT server is not available at 127.0.0.1:19021.

## References

- `references/` directory for additional documentation


rm -rf ~/.claude/skills/rtt-tools/ && cp ~/Projects/my-awesome-skills/skills/rtt-tools ~/.claude/skills/ -r
