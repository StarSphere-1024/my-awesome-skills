---
name: palworld-save-migration
description: Use when moving a Palworld Windows co-op world or host character to a Linux dedicated server, repairing player GUID ownership, migrating guild/building references, or diagnosing PalworldSaveTools fix_host_save.py migrations.
metadata:
  category: self-hosting
  tags: palworld, save-migration, guid, dedicated-server
---

# Palworld Save and Host Migration

## Parameters

Set these variables from the target environment before operating:

```bash
PVE_SSH=your-ssh-alias
VMID=123
SERVICE=palworld.service
SERVER_ROOT=/srv/palworld-server
SAVE_ROOT_REL=Pal/Saved/SaveGames/0
GAME_PORT=8211
TOOL_ROOT=/opt/PalworldSaveTools-v2.1.3
```

These are public example values, not a universal profile. Discover or confirm the host, VMID, service unit, server root, save root, port, and tool version before operating:

```bash
ssh "$PVE_SSH" "set -euo pipefail; hostname; pct status $VMID"
ssh "$PVE_SSH" "pct exec $VMID -- systemctl cat $SERVICE"
ssh "$PVE_SSH" "pct exec $VMID -- test -d '$SERVER_ROOT/$SAVE_ROOT_REL'"
```

The migration must preserve the complete world, original host character progress, Pals, inventory, technology, bases, guild data, and ownership references. Never modify the only active copy. Always retain an untouched pre-migration copy and a full-container backup when possible.

## GUID meaning and direction

Define the IDs before running anything:

- `OLD_GUID`: the Windows co-op host's player file and character identity.
- `NEW_GUID`: the temporary character created by the same account after joining the dedicated server.
- Call the tool as `fix_save(WORK_DIR, NEW_GUID, OLD_GUID)`. Reversing these arguments gives the wrong character ownership.

Worked example values are intentionally omitted; enumerate the target `Players/` directory and verify all three values before use:

```text
OLD_GUID=<WINDOWS_HOST_GUID>
NEW_GUID=<DEDICATED_TEMP_GUID>
WORLD_GUID=<WORLD_GUID>
```

`fix_host_save.py` v2.1.3 requires both characters to be level 2 or higher. If the temporary character is level 1, stop, restart the server, level it to 2, and only then create a fresh work copy. Do not bypass this precondition by editing player levels manually.

## Safe migration sequence

1. Stop the Windows game and Steam client so the source save is not changing.
2. Extract the source archive and identify the complete world directory containing `Level.sav`, `LevelMeta.sav`, `WorldOption.sav`, `LocalData.sav`, and `Players/`.
3. Back up the entire source archive and the target LXC. At minimum, preserve the target active world directory and the target configuration with a timestamped name. Record a file manifest and hashes; file size alone is not validation.
4. Install or start the dedicated server with the world copied into place. Join with the original account and create a temporary character. Leave the server and record its generated `NEW_GUID` from `Players/`.
5. Confirm both GUIDs and both levels from the world data. Stop `$SERVICE`.
6. Copy the active world to a new staging directory on the same filesystem. Run the migration tool only against staging.
7. Parse/round-trip the staged `Level.sav` and every changed player file. Confirm filenames, internal `PlayerUId`, world character-map references, guild references, and owner fields are consistent.
8. Quarantine the original active world by renaming it to an explicit `.pre-migration-<timestamp>` path. Move the validated staging directory into the original active path; do not overlay files, because stale old GUID files can remain.
9. Start the service and verify logs, active state, UDP `$GAME_PORT`, and a real client join. Check the original host's level, inventory, Pals, technology, bases, guild membership, and ownership.
10. Keep the pre-migration world, container backup, tool output, hashes, and logs until the user confirms the game state.

## v2.1.3 tool setup and known entry-point failure

The `PalworldSaveTools` v2.1.3 repository contains a local `palsav` project and local `palooz` native compression extension. Its `requirements.txt` may contain a broken `./src/palsav` path and PyPI cannot resolve the local `palooz` package by name. Install the local packages separately:

```bash
cd "$TOOL_ROOT"
python3 -m pip install --break-system-packages setuptools wheel
python3 -m pip install --break-system-packages --no-build-isolation ./src/palsav/palooz
python3 -m pip install --break-system-packages --no-deps -e ./src/palsav
```

The native extension must expose `palooz.compress` and `palooz.decompress`. If importing the GUI fails with missing `libGL.so.1`, `libfontconfig.so.1`, or `libglib-2.0.so.0`, install the corresponding Debian runtime libraries before testing; do not continue with a partially imported parser.

In the observed v2.1.3 source, `fix_host_save.py` begins with `from import_libs import *`. That module exports `__name__`, so invoking the script directly can silently skip its `if __name__ == '__main__'` CLI block and produce no migration. Do not treat a silent exit as success. Invoke the function explicitly in a staging directory:

```bash
WORK_DIR=/srv/palworld/migration-work-<STAMP>-<WORLD_GUID>
OLD_GUID=<WINDOWS_HOST_GUID>
NEW_GUID=<DEDICATED_TEMP_GUID>
env QT_QPA_PLATFORM=offscreen \
  PYTHONPATH="$TOOL_ROOT/src/palsav:$TOOL_ROOT/src" \
  python3 -u -c "import runpy; d=runpy.run_path('$TOOL_ROOT/src/palworld_toolsets/fix_host_save.py', run_name='tool_module'); g=d['fix_save'].__globals__; g['run_with_loading']=lambda done, task: task(); d['fix_save']('$WORK_DIR', '$NEW_GUID', '$OLD_GUID')"
```

This synchronous callback bypasses the GUI completion dialog; it does not bypass the migration task. The tool swaps player files, rewrites world character-map GUIDs, updates guild/admin/player references, and deep-swaps owner fields. Missing `_dps.sav` files are normal when a player has no DPS file; do not manufacture them. A successful function call returns no useful Boolean, so validate the output files and parsed data rather than trusting the process exit code alone.

## Staging and deployment checks

Before swapping staging into the active path:

- The staging directory contains the expected world files and nonzero player files.
- Both GUID-named player files exist exactly once.
- The player file named `NEW_GUID.sav` contains the old host's progress but internal `PlayerUId=NEW_GUID`; the file named `OLD_GUID.sav` contains the temporary character and internal `PlayerUId=OLD_GUID`.
- `Level.sav` parses and round-trips with the same Palworld-aware tool version.
- The world character map points each character instance to its new GUID.
- Guild admin/member/character handles and build ownership no longer point at the old identity for the migrated host.
- `LevelMeta.sav`, `WorldOption.sav`, and `LocalData.sav` remain present and readable.
- A manifest or hash comparison explains every intentional change.

Use the tool's parser or a Palworld-aware save utility; do not infer validity from `file`, headers, or byte counts. Palworld `.sav` files can be compressed wrappers and version-specific PIM/GVAS formats.

## Post-deployment verification

```bash
ssh "$PVE_SSH" "pct exec $VMID -- systemctl is-active $SERVICE"
ssh "$PVE_SSH" "pct exec $VMID -- journalctl -u $SERVICE --no-pager -n 80"
ssh "$PVE_SSH" "pct exec $VMID -- ss -lun | grep -E ':${GAME_PORT}[[:space:]]'"
```

Require `active`, a log line showing the dedicated server is running on the configured game port, and a successful client join. A parser-only check is not end-to-end proof: verify the actual character and world state in-game.

## Rollback

If parsing fails, the server does not start, or the player/world state is wrong:

1. Stop `$SERVICE`.
2. Quarantine the transformed active directory instead of deleting it.
3. Restore the exact untouched pre-migration world directory or container backup, including ownership and permissions.
4. Start the service and repeat parser, log, port, and client checks.
5. Preserve the failed transformed copy and logs for diagnosis.

Never choose a backup by guessing the newest filename. Use the exact timestamped path and manifest recorded before migration. Never run the tool against the active world, never migrate while the service is writing, and never report success without parser, service, and in-game evidence.

## Common failure modes

- Temporary character is below level 2: level it first; do not edit the save to fake the threshold.
- `fix_host_save.py` prints nothing and exits 0: likely the v2.1.3 `__name__` import bug; use the explicit `runpy` invocation.
- `palooz` imports but lacks `compress`/`decompress`: the editable stub was installed instead of the compiled local extension.
- PIM/GVAS “bad magic” or decompression errors: wrong tool/version, wrong file, or a nonstandard wrapper; restore the backup and inspect the first bytes with a Palworld-aware parser.
- World loads but the player is new: GUID direction or platform identity is wrong; stop and roll back rather than creating more characters.
- Guild/building ownership is broken: the migration was incomplete or ran with an incompatible tool; restore and do not repair individual IDs by hand.
