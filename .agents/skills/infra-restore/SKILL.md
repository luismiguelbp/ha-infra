---
name: infra-restore
description: Restore a managed-infra backup mirror from MANAGED_INFRA_BACKUP to exactly one deployed host.
disable-model-invocation: true
---

# Infra Restore

Push a backup mirror from `MANAGED_INFRA_BACKUP` onto a **single** deployed host. This is a manual operation only and is not part of bootstrap or deploy flows.

## Host parameter

- Required: `--limit <hostname>` using the inventory name from `./bin/infra-list-hosts`, not DNS.
- Optional source override: `-e edge_stack_restore_source=<backup-folder-name>` when the mirror folder name differs from the target host.

Examples in this repo use template names (`edge-node-1`, `edge-node-2`, `edge-node-3`). Live inventory comes from `MANAGED_INFRA_CONFIG`.

## Steps

1. Confirm the repo root.
2. Ensure `MANAGED_INFRA_BACKUP` is set in gitignored `.env`, but do not print secret values.
3. Confirm the mirror exists under `MANAGED_INFRA_BACKUP/<source-host>/`.
4. Bootstrap the target first only if it is a new host: `./bin/infra-bootstrap --limit <host>`.
5. Ping with `./bin/infra-ping --limit <host>`.
6. Run restore with `./bin/infra-restore-edge-stack --limit <host>`.
7. Verify with `./bin/infra-docker-status --limit <host>`.

## Options

```bash
./bin/infra-restore-edge-stack --limit edge-node-1
./bin/infra-restore-edge-stack --limit edge-node-2 -e edge_stack_restore_source=edge-node-1
./bin/infra-restore-edge-stack --limit edge-node-1 -e edge_stack_restore_env=true
./bin/infra-restore-edge-stack --limit edge-node-3 -e edge_stack_restore_stop_services=false
```

## Rules

- Do not read or print secret values from `.env` files.
- Do not commit backup data or mirrored `.env` files.
- Restore overwrites target `data/` directories and imports dumps under `dumps/` when present in the mirror.
- Default restores data only; `.env` stays on the target unless `edge_stack_restore_env=true`.
- If restoring encrypted application data without `.env`, ensure credential secrets on the target match the backup.
- Require exactly one target host with `--limit`.

## Output

Summarize restored runtime data under `/opt/docker/data/` on the target and optional imports from `dumps/` per host profile. Do not print secret file contents.
