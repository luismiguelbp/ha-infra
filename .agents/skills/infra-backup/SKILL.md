---
name: infra-backup
description: Mirror ha-infra edge stack runtime data from one or more hosts to HA_INFRA_BACKUP.
disable-model-invocation: true
---

# Infra Backup

Mirror edge stack runtime data from each host to the control machine under `HA_INFRA_BACKUP`.

## Host parameter

- No parameter: backup all hosts in inventory.
- One hostname: add `--limit <hostname>` using the inventory name from `./bin/infra-list-hosts`, not DNS.

Examples in this repo use template names (`edge-node-1`, `edge-node-2`, `edge-node-3`). Live inventory comes from `HA_INFRA_CONFIG`.

## Steps

1. Confirm the repo root.
2. Ensure `HA_INFRA_BACKUP` is set in gitignored `.env`, but do not print secret values.
3. List hosts with `./bin/infra-list-hosts`.
4. Run backup with `./bin/infra-backup-edge-stack` or `./bin/infra-backup-edge-stack --limit <host>`.
5. Check that the mirror exists under `HA_INFRA_BACKUP/<host>/` without printing secrets.

## Rules

- Do not read or print secret values from `.env` files.
- Do not commit backup data or mirrored `.env` files.
- Keep `HA_INFRA_BACKUP` outside git-tracked directories.

## Output

Summarize each host mirror at `HA_INFRA_BACKUP/<host>/`, including `manifest.json`, mirrored `data/` folders (`data/sqlite/` on autonomous-site hosts), and service dumps under `dumps/` when included in the host profile. Do not print `.env` contents.

Node-RED is stopped briefly by default during backup (`edge_stack_backup_stop_node_red: true`) so `automation.db` is consistent. Document brief downtime when reporting backup results.
