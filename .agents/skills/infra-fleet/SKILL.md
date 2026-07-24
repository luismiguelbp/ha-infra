---
name: infra-fleet
description: Deploy and operate the ha-infra Linux fleet via bin/ scripts and Ansible. Use when running infra-bootstrap, infra-deploy-edge-stack, infra-backup-edge-stack, infra-restore-edge-stack, infra-reboot, fleet status checks, HA_INFRA_CONFIG, Ansible playbooks, or provisioning Docker Compose edge stack services on remote hosts.
---

# ha-infra fleet operations

Infrastructure-as-code for a small Linux server fleet. Run all commands from the **ha-infra repo root** on your control machine.

Follow `AGENTS.md`: examples in this repo use fictional names (`edge-node-1`, `site-a`); live deploys use inventory from `HA_INFRA_CONFIG`. Do not copy production hostnames or DNS aliases into committed files here.

## Edge stack profiles

| Profile | Services | Template host |
|---------|----------|---------------|
| **Autonomous site** | Node-RED, Mosquitto, SQLite mount | edge-node-2 |
| **Home history tier** | PostgreSQL, Grafana | edge-node-3 |
| **Full lab** | All services | edge-node-1 |

SQLite (`data/sqlite/automation.db`) is a file bind-mounted into Node-RED — not a Compose service. Do not assume PostgreSQL or Grafana belong on autonomous site hosts.

## Two-repo model

| Repo | Role |
|------|------|
| `ha-infra` | Playbooks, roles, templates, wrapper scripts, and example inventory |
| External config clone | Real inventory, secrets, production Compose files, and tuned data files |

Set `HA_INFRA_CONFIG` in gitignored `.env`. Every `bin/ansible-*` and `bin/infra-*` script validates this path and refuses template directories.

**Never** read, echo, or commit secrets from the external config source (`.env`, `passwords_file`, credential hashes, or production service config).

## Prerequisites

- Ansible: `brew install ansible`
- Collections: `ansible-galaxy collection install -r ansible/requirements.yml`
- `.env` with valid `HA_INFRA_CONFIG`
- SSH key access and passwordless sudo on each host (`docs/ansible.md`)

## Script picker

| Goal | Script |
|------|--------|
| Full fleet provisioning | `./bin/infra-bootstrap` |
| Edge stack only | `./bin/infra-deploy-edge-stack` |
| Configure Samba public share | `./bin/infra-configure-samba` |
| Docker and system status | `./bin/infra-docker-status` |
| Backup edge stack data | `./bin/infra-backup-edge-stack` |
| Deploy site catalog | `./bin/infra-deploy-catalog` (see `infra-deploy-catalog` skill) |
| Restore backup mirror to one host | `./bin/infra-restore-edge-stack` |
| Reboot fleet | `./bin/infra-reboot` |
| Connectivity check | `./bin/infra-ping` |
| List inventory hosts | `./bin/infra-list-hosts` |

All scripts accept Ansible extras: `--limit <host>`, `--check`, `-e key=value`.

At runtime, host names come from `$HA_INFRA_CONFIG/ansible/inventory/hosts.yml` (inventory name, not DNS). Template examples are `edge-node-1`, `edge-node-2`, and `edge-node-3`.

## Deploy workflow

1. Run `./bin/infra-list-hosts` to confirm targets.
2. Run `./bin/infra-ping` to verify SSH. Add `--limit edge-node-1` for one host.
3. Run the chosen script. Add `--limit <host>` for staged rollout.
4. Verify with `./bin/infra-docker-status`.

## Full vs edge-only

- New host or infra change: use `./bin/infra-bootstrap`.
- Compose/config change only: use `./bin/infra-deploy-edge-stack`.

## Safety defaults

- Prefer `--limit edge-node-1` or another single host for first production runs or risky changes.
- Do not use `--check` alone to validate UFW on fresh hosts.
- Ansible copies `docker/.env` from config-src when present; containers start only when `.env` exists on the host.
- Manually configured runtime files under `/opt/docker/data/` on the host are not overwritten by Ansible.

## Status checks

```bash
./bin/infra-docker-status
./bin/infra-docker-status --limit edge-node-1
```

## Backup mirrors

Set `HA_INFRA_BACKUP` in gitignored `.env`, then run:

```bash
./bin/infra-backup-edge-stack
./bin/infra-backup-edge-stack --limit edge-node-1
```

Each run mirrors runtime files into `HA_INFRA_BACKUP/<host>/` with no timestamp subfolders. Autonomous-site mirrors include `data/sqlite/`; Node-RED stops briefly by default during backup for a consistent `automation.db`.

## Restore backup mirrors

Manual disaster recovery only. This is not part of bootstrap or deploy.

```bash
./bin/infra-restore-edge-stack --limit edge-node-1
./bin/infra-restore-edge-stack --limit edge-node-2 -e edge_stack_restore_source=edge-node-1
```

Requires `--limit` with exactly one host. Default source folder matches the limited host; override with `edge_stack_restore_source`. Restores `data/` and service dumps under `dumps/` only unless `-e edge_stack_restore_env=true`.

## Credentials

Per-service credentials are manual and not stored in Ansible vars. See `docker/README.md#credentials`.

## Reference

- Full script table and options: `docs/ansible.md`
- Edge stack layout and credentials: `docker/README.md`
- Template inventory: `ansible/inventory/`
