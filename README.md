# My Awesome Skills

English | [中文](README.zh-CN.md)

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for embedded systems development, firmware debugging, and general software engineering workflows.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| [rtt-tools](skills/rtt-tools/) | `/rtt-tools` | SEGGER J-Link RTT capture, command, and interactive console for Zephyr RTOS targets |
| [mcu-gdb-debugger](skills/mcu-gdb-debugger/) | `/mcu-gdb-debugger` | MCU firmware debugging with GDB and gdbserver backends (OpenOCD, pyOCD, J-Link, QEMU) |
| [linux-gdb-debugger](skills/linux-gdb-debugger/) | `/linux-gdb-debugger` | Linux user-space C/C++ debugging for crashes, core dumps, hangs, and stepping |
| [git_commit](skills/git_commit/) | `/git_commit` | Conventional Commit helper that inspects staged changes and commits with a formatted message |
| [generate-agentic-prompt](skills/generate-agentic-prompt/) | `/generate-agentic-prompt` | Interactive prompt compiler that infers your domain and produces structured implementation prompts |

## Installation

Add this repository as a skill source in your Claude Code settings:

```bash
# Clone the repo
git clone https://github.com/StarSphere-1024/my-awesome-skills.git

# Add to Claude Code settings (adjust path as needed)
claude config add skills /path/to/my-awesome-skills/skills
```

Or configure manually in `~/.claude/settings.json`:

```json
{
  "skills": ["/path/to/my-awesome-skills/skills"]
}
```

### External Dependencies

Some skills require additional tools on your system:

| Skill | Requirements |
|-------|-------------|
| rtt-tools | Python 3, SEGGER J-Link software (`JLinkGDBServer`), GDB |
| mcu-gdb-debugger | Cross GDB (e.g. `arm-none-eabi-gdb`), a gdbserver backend (OpenOCD, pyOCD, J-Link GDB Server, etc.) |
| linux-gdb-debugger | GDB |
| git_commit | Git |
| generate-agentic-prompt | None |

## Usage

Invoke any skill via slash command in Claude Code:

```
/rtt-tools capture --elf build/zephyr/zephyr.elf
/git_commit
/linux-gdb-debugger
/mcu-gdb-debugger
/generate-agentic-prompt
```

## Testing

```bash
pytest tests/
```

## License

[GNU AGPL v3](LICENSE)
