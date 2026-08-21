# My Awesome Skills

[English](README.md) | 中文

一套 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 技能集合，面向嵌入式开发、软件工程、调试和个人自托管基础设施管理。

## 工程工作流

| 技能 | 命令 | 说明 |
|------|------|------|
| [codebase-first-engineering](skills/codebase-first-engineering/) | `/codebase-first-engineering` | 面向现有代码库的系统化侦察与最小一致性修改 |
| [clarify-requirements](skills/clarify-requirements/) | `/clarify-requirements` | 针对模糊工程需求进行聚焦澄清 |
| [generate-agentic-prompt](skills/generate-agentic-prompt/) | `/generate-agentic-prompt` | 生成结构化实现提示词的交互式编译器 |
| [git_commit](skills/git_commit/) | `/git_commit` | 检查暂存区并生成 Conventional Commit |

## 嵌入式与 Zephyr

| 技能 | 命令 | 说明 |
|------|------|------|
| [rtt-tools](skills/rtt-tools/) | `/rtt-tools` | 面向 Zephyr 目标的 SEGGER J-Link RTT 抓取与交互控制台 |
| [zephyr-clangd](skills/zephyr-clangd/) | `/zephyr-clangd` | Zephyr 和 nRF Connect SDK 的 clangd/LSP 配置 |
| [zephyr-testing](skills/zephyr-testing/) | `/zephyr-testing` | 使用 Ztest、Twister、native_sim、QEMU 和硬件进行 Zephyr 测试 |

## 调试

| 技能 | 命令 | 说明 |
|------|------|------|
| [mcu-gdb-debugger](skills/mcu-gdb-debugger/) | `/mcu-gdb-debugger` | 使用 GDB 和 gdbserver 后端进行 MCU 固件调试 |
| [linux-gdb-debugger](skills/linux-gdb-debugger/) | `/linux-gdb-debugger` | 面向崩溃、core dump 和挂起的 Linux 用户态 C/C++ 调试 |

## 可视化

| 技能 | 命令 | 说明 |
|------|------|------|
| [mermaid-layout](skills/mermaid-layout/) | `/mermaid-layout` | Mermaid 图布局与拓扑优化 |

## 自托管与服务器运维

| 技能 | 命令 | 说明 |
|------|------|------|
| [server-admin](skills/server-admin/) | `/server-admin` | 注重隐私的 SSH、PVE、LXC、VM、服务、备份和部署操作 |
| [pve-palworld-server-config](skills/pve-palworld-server-config/) | `/pve-palworld-server-config` | Proxmox LXC 内 Palworld 专用服务器的安全配置修改 |
| [palworld-save-migration](skills/palworld-save-migration/) | `/palworld-save-migration` | Palworld 联机世界迁移到专用服务器及玩家所有权修复 |

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

部分技能需要系统工具或目标环境访问权限：

| 技能 | 依赖 |
|------|------|
| rtt-tools | Python 3、SEGGER J-Link 软件（`JLinkGDBServer`）、GDB |
| zephyr-clangd | clangd、生成 `compile_commands.json` 的 Zephyr/NCS 构建环境及匹配编译器 |
| zephyr-testing | Zephyr `west`、Twister、pytest，以及目标模拟器或硬件 |
| mcu-gdb-debugger | 交叉编译 GDB、gdbserver 后端及目标探针或 QEMU |
| linux-gdb-debugger | GDB |
| git_commit | Git |
| server-admin | 已配置的 SSH 别名；homelab 流程还需要私有 inventory |
| pve-palworld-server-config | 已验证的 Proxmox SSH 访问、`pct`、systemd、Python 3 和 Palworld 服务端 |
| palworld-save-migration | SSH 访问、Python 3、PalworldSaveTools 及本地 `palooz` 压缩扩展 |
| generate-agentic-prompt、clarify-requirements、codebase-first-engineering、mermaid-layout | 无 |

## 使用

在 Claude Code 中通过斜杠命令调用任意技能：

```text
/zephyr-testing
/mcu-gdb-debugger
/linux-gdb-debugger
/server-admin
/pve-palworld-server-config
/palworld-save-migration
/git_commit
```

## 测试

```bash
pytest tests/
```

## 许可证

[GNU AGPL v3](LICENSE)
