# My Awesome Skills

English | [中文](README.zh-CN.md)

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills for embedded development, software engineering, debugging, and personal self-hosting infrastructure.

## Engineering Workflows

| Skill | Command | Description |
|-------|---------|-------------|
| [codebase-first-engineering](skills/codebase-first-engineering/) | `/codebase-first-engineering` | System-aware reconnaissance and smallest coherent code changes |
| [clarify-requirements](skills/clarify-requirements/) | `/clarify-requirements` | Focused clarification for ambiguous engineering requirements |
| [generate-agentic-prompt](skills/generate-agentic-prompt/) | `/generate-agentic-prompt` | Interactive compiler for structured implementation prompts |
| [git_commit](skills/git_commit/) | `/git_commit` | Conventional Commit helper for staged changes |

## Embedded and Zephyr

| Skill | Command | Description |
|-------|---------|-------------|
| [rtt-tools](skills/rtt-tools/) | `/rtt-tools` | SEGGER J-Link RTT capture and interactive console for Zephyr targets |
| [zephyr-clangd](skills/zephyr-clangd/) | `/zephyr-clangd` | clangd/LSP configuration for Zephyr and nRF Connect SDK |
| [zephyr-testing](skills/zephyr-testing/) | `/zephyr-testing` | Zephyr testing with Ztest, Twister, native_sim, QEMU, and hardware |

## Debugging

| Skill | Command | Description |
|-------|---------|-------------|
| [mcu-gdb-debugger](skills/mcu-gdb-debugger/) | `/mcu-gdb-debugger` | MCU firmware debugging with GDB and gdbserver backends |
| [linux-gdb-debugger](skills/linux-gdb-debugger/) | `/linux-gdb-debugger` | Linux user-space C/C++ debugging for crashes, core dumps, and hangs |

## Visualization

| Skill | Command | Description |
|-------|---------|-------------|
| [mermaid-layout](skills/mermaid-layout/) | `/mermaid-layout` | Mermaid diagram layout and topology optimization |

## Self-Hosting and Server Administration

| Skill | Command | Description |
|-------|---------|-------------|
| [server-admin](skills/server-admin/) | `/server-admin` | Privacy-conscious SSH, PVE, LXC, VM, service, backup, and deployment operations |
| [pve-palworld-server-config](skills/pve-palworld-server-config/) | `/pve-palworld-server-config` | Safe Palworld dedicated-server configuration changes inside a Proxmox LXC |
| [palworld-save-migration](skills/palworld-save-migration/) | `/palworld-save-migration` | Palworld co-op-to-dedicated-server save and player ownership migration |

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

Some skills require additional tools or access on your system:

| Skill | Requirements |
|-------|-------------|
| rtt-tools | Python 3, SEGGER J-Link software (`JLinkGDBServer`), GDB |
| zephyr-clangd | clangd, a Zephyr/NCS build with `compile_commands.json`, and the matching compiler |
| zephyr-testing | Zephyr `west`, Twister, pytest, and any target-specific simulator or hardware |
| mcu-gdb-debugger | Cross GDB, a gdbserver backend, and the target/probe or QEMU |
| linux-gdb-debugger | GDB |
| git_commit | Git |
| server-admin | A configured SSH alias; private inventory is optional for generic examples but required by the homelab workflow |
| pve-palworld-server-config | SSH access to the verified Proxmox host, `pct`, systemd, Python 3, and a Palworld server |
| palworld-save-migration | SSH access, Python 3, PalworldSaveTools, and its local `palooz` compression extension |
| generate-agentic-prompt, clarify-requirements, codebase-first-engineering, mermaid-layout | None |

## Usage

Invoke any skill via slash command in Claude Code:

```text
/zephyr-testing
/mcu-gdb-debugger
/linux-gdb-debugger
/server-admin
/pve-palworld-server-config
/palworld-save-migration
/git_commit
```

## Testing

```bash
pytest tests/
```

## License

[GNU AGPL v3](LICENSE)
