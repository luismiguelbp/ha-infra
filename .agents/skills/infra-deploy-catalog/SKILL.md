---
name: infra-deploy-catalog
description: Deploy catalog.json to one autonomous site host via infra-deploy-catalog. Use when pushing catalog.json, restarting Node-RED for catalog upsert, or running Ansible deploy-catalog.yml with --catalog-src.
disable-model-invocation: true
---

# Infra deploy catalog

Copy a `catalog.json` file to one autonomous site host and restart Node-RED so the catalog upsert flow runs.

Run from the **ha-infra repo root**.

Follow `AGENTS.md`: examples use fictional names (`edge-node-2`, `site-a`); live hosts come from `HA_INFRA_CONFIG`. Do not copy production hostnames into committed files.

## Prerequisites

- `.env` with valid `HA_INFRA_CONFIG`
- Absolute path to an existing `catalog.json` on the control machine
- Target host profile includes `compose-node-red.yml` and `data/catalog`
- SSH access; prefer `./bin/infra-ping --limit <host>` first when connectivity is uncertain

## Workflow

1. List hosts: `./bin/infra-list-hosts`
2. Deploy to exactly one inventory host:

```bash
./bin/infra-deploy-catalog --catalog-src /absolute/path/to/catalog.json --limit edge-node-2
```

3. Playbook actions:
   - Ensure `data/catalog` exists on the host
   - Copy source file to `${edge_stack_path}/data/catalog/catalog.json` (default `/opt/docker/data/catalog/catalog.json`)
   - `docker compose restart node-red` when `/opt/docker/.env` exists

4. Node-RED reads `/data/catalog/catalog.json` and upserts catalog tables into SQLite. Telemetry, events, and snapshots are untouched.

`--limit` must name a single inventory hostname (no commas, wildcards, or multi-host patterns).

## Prefer ha-apps wrapper when available

From ha-apps (resolves `HA_APPS_CONFIG/<location>/catalog.json` and needs `HA_INFRA_ROOT`):

```bash
./bin/ha-db-catalog-deploy --config ha-site-a --limit edge-node-2
```

Use this infra skill when calling Ansible/infra directly or when the catalog path is already absolute.

## Rules

- Not part of `infra-deploy-edge-stack` / bootstrap — those only seed starter `catalog.json` when missing.
- Do not deploy catalog to home history-tier hosts (PostgreSQL/Grafana only).
- Do not read or print secrets from `.env`, `passwords_file`, or production config.
- Confirm the `--limit` host with the user when the target is unclear.

## References

- `docs/ansible.md` — Deploy site catalog
- `ansible/playbooks/deploy-catalog.yml`
- `docker/README.md` — catalog + SQLite mounts
- ha-apps skill `ha-db-catalog-deploy`
- ha-apps `docs/database/catalog-deploy.md`
