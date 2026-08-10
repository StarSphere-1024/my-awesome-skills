# My Awesome Skills

[English](README.md) | 中文

一套 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能集合，面向嵌入式系统开发、固件调试和通用软件工程工作流。

## 技能列表

| 技能 | 命令 | 说明 |
|------|------|------|
| [rtt-tools](skills/rtt-tools/) | `/rtt-tools` | SEGGER J-Link RTT 抓取、命令发送和交互式控制台，用于 Zephyr RTOS 目标 |
| [mcu-gdb-debugger](skills/mcu-gdb-debugger/) | `/mcu-gdb-debugger` | MCU 固件 GDB 调试，支持多种 gdbserver 后端（OpenOCD、pyOCD、J-Link、QEMU） |
| [linux-gdb-debugger](skills/linux-gdb-debugger/) | `/linux-gdb-debugger` | Linux 用户态 C/C++ 调试，覆盖崩溃、core dump、挂起和单步执行 |
| [git_commit](skills/git_commit/) | `/git_commit` | Conventional Commit 辅助工具，检查暂存区变更并生成规范提交信息 |
| [generate-agentic-prompt](skills/generate-agentic-prompt/) | `/generate-agentic-prompt` | 交互式提示词编译器，自动推断开发领域并生成结构化的实现提示词 |
| [mermaid-layout](skills/mermaid-layout/) | `/mermaid-layout` | Mermaid 图布局与拓扑优化，减少边交叉并保持业务语义不变 |

## 安装

将本仓库添加为 Claude Code 的技能源：

```bash
# 克隆仓库
git clone https://github.com/StarSphere-1024/my-awesome-skills.git

# 添加到 Claude Code 配置（根据实际路径调整）
claude config add skills /path/to/my-awesome-skills/skills
```

或手动编辑 `~/.claude/settings.json`：

```json
{
  "skills": ["/path/to/my-awesome-skills/skills"]
}
```

### 外部依赖

部分技能需要系统中安装额外工具：

| 技能 | 依赖 |
|------|------|
| rtt-tools | Python 3、SEGGER J-Link 软件（`JLinkGDBServer`）、GDB |
| mcu-gdb-debugger | 交叉编译 GDB（如 `arm-none-eabi-gdb`）、gdbserver 后端（OpenOCD、pyOCD、J-Link GDB Server 等） |
| linux-gdb-debugger | GDB |
| git_commit | Git |
| generate-agentic-prompt | 无 |

## 使用

在 Claude Code 中通过斜杠命令调用任意技能：

```
/rtt-tools capture --elf build/zephyr/zephyr.elf
/git_commit
/linux-gdb-debugger
/mcu-gdb-debugger
/generate-agentic-prompt
```

## 测试

```bash
pytest tests/
```

## 许可证

[GNU AGPL v3](LICENSE)
