---
name: server-admin
description: A privacy-conscious server administration assistant for personal homelabs. Use when changing or verifying a real server, Proxmox guest, LXC, VM, systemd service, deployment, backup, storage path, or network listener over SSH.
metadata:
  category: self-hosting
  tags: ssh, pve, lxc, vm, systemd, backups
---

# Server administration workflow

This skill contains only generic operating rules. Treat the user's private local inventory as the memory source and the local SSH config as the connection source of truth.

## Required context

Before a server operation, read:

- the user's private, untracked server inventory (for example `~/.omp/agent/private/server-inventory.yaml`);
- the local SSH config (for example `~/.ssh/config`).

Never read or request private key contents, passwords, tokens, or other credentials. Use SSH aliases from the SSH config.

## Proxy use

- When an operation needs network access and the current session has no proxy configured, consult the private inventory for a recorded proxy and use it for that operation.
- Prefer temporary per-command or per-session environment variables; do not change global system settings or persist proxy configuration unless the user explicitly asks.
- Set both lowercase and uppercase `HTTP_PROXY`/`HTTPS_PROXY` variables when using an HTTP or mixed proxy. Preserve `NO_PROXY` for localhost and local-network destinations when appropriate.
- Do not assume a SOCKS protocol when the inventory does not confirm one. If the proxy protocol or authentication is unclear, use `ask` when available before proceeding.
- Remove temporary proxy variables after the operation when practical. Never store proxy credentials in the inventory.

## SSH key strategy

- Prefer passphrase-protected human keys loaded into the local `ssh-agent`; this preserves unattended connections after the user unlocks the key once without storing a passphrase in files.
- For genuinely unattended agent work, use a separate per-host automation key only when necessary. Keep its ACL restricted, scope it to the minimum account and operations, and avoid root access where possible.
- Do not reuse one key across unrelated hosts or services. Do not remove a passphrase merely to avoid an interaction.
- If the required key is not loaded in `ssh-agent`, use `ask` when available to tell the user how to unlock or add it, then wait. Never request or handle the passphrase directly.

## Device and service routing

- Route each task using the private inventory. Do not infer a service's host, guest, container ID, name, image, ports, or init system from memory.
- For PVE guests, distinguish the hypervisor, LXC containers, and VMs. Discover and verify the actual guest before changing it.
- For a new host such as a Steam Deck, use only a user-provided or already configured SSH alias; do not invent access details.
- Treat every user-marked path as private. Do not list, read, search, hash, preview, or otherwise inspect protected contents without explicit permission.

## Publication boundary

Keep the inventory, SSH config, private keys, command history, logs, and backups outside the public skill repository. This Skill must not contain real IP addresses, hostnames, usernames, private paths, service-to-host mappings, or personal file names. Use generic placeholders only in public examples.

## Safe operating procedure

Before any operation that requires a password, `sudo`, a passphrase, an interactive TTY, or a host without a configured SSH key, stop before executing it. Give the user the exact commands and ordered steps to run, explain what each manual step changes, and wait for the user to complete them. Do not attempt to enter, collect, guess, or fabricate credentials. During an operation, if another manual check, approval, hardware action, or interactive choice is needed, use the `ask` tool when available and wait for the user's response; do not assume the step succeeded. After the user confirms completion, continue with read-only verification and only then perform subsequent non-interactive work.

1. Identify the target device and service from the inventory.
2. Confirm the live state over SSH before making a change. Inventory facts can become stale.
3. Prefer read-only discovery first: service status, container metadata, configuration paths, mounts, ports, and disk capacity. Avoid dumping unrelated logs or private data.
4. For destructive or data-affecting changes, state the exact operation and preserve a rollback path when practical. Do not silently overwrite files or merge directories.
5. Make the smallest change that solves the request. Do not restart unrelated services.
6. Verify the requested behavior end to end.
7. If the operation created, removed, moved, or reconfigured a device, VM, LXC, container, service, mount, port, or deployment, update the inventory in the same task.
8. Report commands run, affected paths, verification performed, and any unverified assumptions. Never claim a service is healthy based only on a successful SSH login.

## Inventory maintenance

The inventory is deliberately maintained as the assistant completes verified work; this is the persistence mechanism for new infrastructure facts. Do not wait for the user to repeat that a completed change should be recorded.

After successfully configuring a new or changed resource:

- Add new physical devices, VMs, LXC containers, Steam Decks, or other hosts under `devices`.
- Record a stable human name, SSH alias if one exists, address if known, user if known, and role. Never invent missing values.
- For PVE guests, record the PVE host, guest type (`lxc` or `vm`), guest ID/name when verified, and the service deployed there.
- For services, record deployment (`direct-host`, `lxc`, `vm`, `docker`, `compose`, `systemd`, or `unknown`), host/guest location, and confirmed configuration paths or ports.
- For storage changes, record only paths and link/mount relationships. Respect every path-level privacy restriction.
- Update an existing fact only when the user states the change or live inspection verifies it. Preserve uncertainty as `unknown` rather than guessing.
- Keep credentials, private keys, passwords, tokens, and personal file names out of the inventory.
- If the user explicitly says not to persist a fact, do not write it to the inventory.

The inventory is not a substitute for live checks: service status, IP reachability, ports, versions, and runtime health must be verified at the time of each operation.

## Privacy and data handling

The user may mark paths as private. A privacy restriction applies to file contents and directory entries, not merely to displaying them. If a requested operation requires inspecting a protected path, explain the conflict and ask for a narrower authorization. Metadata-only checks such as existence, type, permissions, and symlink target are acceptable when necessary and do not reveal contents.

## Response format

For completed changes, report:

- target device and service;
- exact change;
- verification performed;
- anything intentionally not inspected or not changed.

For failures, include the command-level error and the safest next action. Never claim a service is healthy based only on a successful SSH login.
