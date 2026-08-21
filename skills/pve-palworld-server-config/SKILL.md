---
name: pve-palworld-server-config
description: Use when managing Palworld dedicated-server settings inside a Proxmox LXC over SSH, including death drops, egg hatching, rates, ports, or other PalWorldSettings.ini changes; also use for requests to verify, summarize, or roll back those changes.
metadata:
  category: self-hosting
  tags: palworld, proxmox, lxc, server-config
---

# PVE Palworld Server Configuration

## Parameters

Set these control-machine variables from the target environment before operating:

```bash
PVE_SSH=your-ssh-alias
VMID=123
SERVICE=palworld.service
ROOT=/srv/palworld-server
CFG_REL=Pal/Saved/Config/LinuxServer/PalWorldSettings.ini
TEMPLATE_REL=DefaultPalWorldSettings.ini
GAME_PORT=8211
```

These are public example values, not a universal profile. Discover or confirm the host, VMID, service unit, server root, config path, and port before changing a host:

```bash
ssh "$PVE_SSH" "set -euo pipefail; hostname; pct status $VMID"
ssh "$PVE_SSH" "pct exec $VMID -- systemctl cat $SERVICE"
ssh "$PVE_SSH" "pct exec $VMID -- test -f '$ROOT/$CFG_REL'"
```

Use the configured SSH alias or an explicitly supplied connection method; do not infer an identity file or IP address. The live config is inside the LXC, not on the Proxmox host. This skill changes server settings, not save files. Do not use it for Steam identity migration, player GUID repair, or world-save conversion.

## Operating rule

Treat `PalWorldSettings.ini` as a structured `OptionSettings=(...)` record, usually one long line. Change exactly one named token and preserve every other byte. Never replace the live file with a hand-written partial config, append a second `OptionSettings` line, or claim success without post-restart output proving it.

Use this sequence:

1. Verify the target host, VMID, service, config path, and current value.
2. Stop the server before writing the file.
3. Create a timestamped backup of the live config.
4. If the live config is empty, use `DefaultPalWorldSettings.ini` as the starting content; otherwise edit only the existing key.
5. Require exactly one occurrence of the key. Missing or duplicate keys are errors, not reasons to guess.
6. Replace only the value using a bytes-preserving temporary file and atomic rename.
7. Start the service and verify its active state, the persisted value, recent logs, and UDP listeners.
8. Keep the printed backup path for rollback.

## Safe edit pattern

Run from the control machine. Set `KEY` and `VALUE`, then set the target profile variables from the Parameters section.

```bash
KEY=DeathPenalty VALUE=None
ssh "$PVE_SSH" "set -euo pipefail; hostname; pct status $VMID; pct exec $VMID -- bash -s -- '$SERVICE' '$ROOT' '$CFG_REL' '$TEMPLATE_REL' '$KEY' '$VALUE' '$GAME_PORT'" <<'REMOTE'
set -euo pipefail
SERVICE="$1"
ROOT="$2"
CFG_REL="$3"
TEMPLATE_REL="$4"
KEY="$5"
VALUE="$6"
GAME_PORT="$7"
CFG="$ROOT/$CFG_REL"
TEMPLATE="$ROOT/$TEMPLATE_REL"

systemctl is-active --quiet "$SERVICE" || {
  echo "ERROR: $SERVICE is not active" >&2
  exit 1
}
test -f "$CFG"
test -f "$TEMPLATE"

systemctl stop "$SERVICE"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$CFG.bak.$STAMP"
cp -a -- "$CFG" "$BACKUP"

python3 - "$CFG" "$TEMPLATE" "$KEY" "$VALUE" <<'PY'
from pathlib import Path
import os
import re
import sys

cfg, template = map(Path, sys.argv[1:3])
key, value = sys.argv[3:]
data = cfg.read_bytes()
if not data.strip():
    data = template.read_bytes()

needle = key.encode()
pattern = rb"(?<![A-Za-z0-9_])" + re.escape(needle) + rb"=([^,)]*)"
matches = list(re.finditer(pattern, data))
if len(matches) != 1:
    raise SystemExit(f"{key}: expected exactly one assignment, found {len(matches)}")

replacement = needle + b"=" + value.encode()
updated = data[:matches[0].start()] + replacement + data[matches[0].end():]
tmp = cfg.with_name(cfg.name + ".tmp")
tmp.write_bytes(updated)
os.replace(tmp, cfg)
print(f"updated {key}={value}")
PY

systemctl start "$SERVICE"
systemctl is-active --quiet "$SERVICE"
python3 - "$CFG" "$KEY" "$VALUE" <<'PY'
from pathlib import Path
import re
import sys

cfg, key, value = sys.argv[1:]
data = Path(cfg).read_bytes()
pattern = rb"(?<![A-Za-z0-9_])" + re.escape(key.encode()) + rb"=" + re.escape(value.encode()) + rb"(?=[,)]|\r?$)"
if len(list(re.finditer(pattern, data))) != 1:
    raise SystemExit(f"post-restart verification failed: {key}={value}")
print(f"verified {key}={value}")
PY

journalctl -u "$SERVICE" --no-pager -n 20
ss -lun | grep -E ":${GAME_PORT}[[:space:]]"
printf 'backup=%s\n' "$BACKUP"
REMOTE
```

The Python expression deliberately refuses absent or duplicate keys. The temporary file plus `os.replace` avoids leaving a partially written config. The template is used only when the live config is empty; it is never edited.

## Common settings

These are examples, not a universal schema. Confirm each key and its allowed value in the target's live config or installed template before changing it.

| Request | Example key/value | Meaning |
|---|---|---|
| Disable death drops | `DeathPenalty=None` | No item/equipment drop on death for the observed Palworld build. |
| Hatch eggs immediately | `PalEggDefaultHatchingTime=0.000000` | Zero incubation-time multiplier. |
| Restore template hatching time | `PalEggDefaultHatchingTime=1.000000` | The default multiplier observed in this deployment. |

For rates such as `ExpRate`, `PalCaptureRate`, `CollectionDropRate`, or `EnemyDropItemRate`, inspect the target first. Do not assume a key exists or that its value semantics are stable across Palworld versions.

## Verification requirements

A completed change requires all of the following observed results:

```bash
PVE_SSH=your-ssh-alias VMID=123 SERVICE=palworld.service GAME_PORT=8211
ssh "$PVE_SSH" "pct exec $VMID -- systemctl is-active $SERVICE"
ssh "$PVE_SSH" "pct exec $VMID -- journalctl -u $SERVICE --no-pager -n 80"
ssh "$PVE_SSH" "pct exec $VMID -- ss -lun | grep -E ':${GAME_PORT}[[:space:]]'"
```

The service must be `active`, the requested key/value must still be present after restart, and the logs must show the server reached its listening state. UDP `27015` is optional; do not report it as required when it is not listening.

## Rollback

Use the exact backup path printed by the edit command, never the newest file guessed from a directory listing:

```bash
ssh "$PVE_SSH" "pct exec $VMID -- systemctl stop $SERVICE && pct exec $VMID -- cp -a -- '/path/to/PalWorldSettings.ini.bak.TIMESTAMP' '$ROOT/$CFG_REL' && pct exec $VMID -- systemctl start $SERVICE"
```

Then repeat the service, log, listener, and configuration checks. If startup fails, stop making changes and report the exact `systemctl status` and `journalctl` output.

## Common mistakes

- Ignoring the target's configured SSH alias/key and connecting to an unverified host.
- Editing `DefaultPalWorldSettings.ini`; it is a sample template and is not the live config.
- Writing only `DeathPenalty=None` into an otherwise empty file; Palworld needs the complete `OptionSettings=(...)` record.
- Replacing the entire line to change one setting and silently losing unrelated settings.
- Modifying while the server is running, causing a lost write or a config rewrite.
- Checking only the file before restart; the server can rewrite or reject configuration during startup.
- Claiming a remote change was completed when no command output was observed.
