# Ansible

Manage the Linux fleet from your Mac. Inventory is the source of truth for hostnames and DNS names.

## Fleet inventory

| Host | Group | DNS | Location |
|------|-------|-----|----------|
| edge-node-1 | `linux_hosts` | edge-node-1.example.lan | site-a |
| edge-node-2 | `linux_hosts` | edge-node-2.example.lan | site-b |
| edge-node-3 | `linux_hosts_standby` | edge-node-3.example.lan | site-c |

Playbooks target `linux_hosts` only. Hosts in `linux_hosts_standby` stay in inventory (with `host_vars`) but are skipped by fleet-wide deploys. Deploy a standby host explicitly with `--limit edge-node-3`.

Files:

- `ansible/inventory/hosts.yml` — hosts, groups, and `ansible_host`
- `ansible/inventory/host_vars/` — per-host metadata and edge stack profile
- `ansible/inventory/group_vars/linux_hosts.yml` — shared defaults for active hosts
- `ansible/inventory/group_vars/linux_hosts_standby.yml` — shared defaults for standby hosts

### Edge stack profiles (template inventory)

Each host declares which Compose services it runs via `edge_stack_compose_files` and matching `edge_stack_data_dirs` in `host_vars/`. The `edge_stack` role copies only those files, creates the data dirs, opens the right firewall ports, and sets `COMPOSE_FILE` on each Pi from the host profile.

| Host | Profile | Compose services |
|------|---------|------------------|
| edge-node-1 | Full lab | Portainer, Node-RED, Mosquitto, PostgreSQL, Grafana |
| edge-node-2 | Autonomous site | Node-RED, Mosquitto, SQLite mount |
| edge-node-3 | Home history tier | PostgreSQL, Grafana |

**Autonomous site** hosts run Node-RED + Mosquitto with a mounted SQLite automation database (`data/sqlite/automation.db`). Each site is independent — no PostgreSQL or Grafana required.

**Home history tier** hosts run PostgreSQL + Grafana for long-term telemetry/events and cross-site dashboards. Import site catalogs into this PostgreSQL instance when central history is enabled (see ha-apps `ha-db-portal`).

Production inventory in `HA_INFRA_CONFIG` should mirror the same pattern (autonomous site hosts and a home history tier host) while keeping real hostnames and DNS details out of this repository.

**`edge_stack_data_files`** — the role default copies starter files from `docker/data/` to the host when missing (`mosquitto.conf`, `passwords_file`, `settings.js`, `automation.db`). Ansible never overwrites files that already exist on the host.

| Host | `edge_stack_data_files` | Behaviour |
|------|-------------------------|-----------|
| edge-node-2 | *(omitted)* | Inherits role defaults; seeds MQTT/Node-RED files when missing |
| edge-node-3 | `[]` | Skips file copy entirely — use for database/metrics-only hosts |

Example for a host without Mosquitto or Node-RED (see `host_vars/edge-node-3.yml`):

```yaml
edge_stack_data_files: []
```

Full-stack or autonomous site hosts should omit this key (or list only the files you want seeded). Do not set `[]` on hosts that run Mosquitto unless you plan to provide `mosquitto.conf` and `passwords_file` manually.

Database-only hosts also set `firewall_edge_ports` for Grafana (3000) and PostgreSQL (5432) instead of the MQTT defaults (1880, 1883). Hosts that include Portainer should allow 9443.

## Prerequisites

- Ansible on the Mac: `brew install ansible`
- Ansible collections (once): `ansible-galaxy collection install -r ansible/requirements.yml`
- SSH key access to each Pi — [SSH keys: Mac to Linux](ssh-keys-mac-to-linux.md)
- Pis reachable at their DNS names from the Mac (local DNS or `/etc/hosts`)

Optional `~/.ssh/config` entries can use the same host aliases as inventory:

```ssh-config
Host edge-node-1
    HostName edge-node-1.example.lan
    User user
    IdentityFile ~/.ssh/id_ed25519

Host edge-node-2
    HostName edge-node-2.example.lan
    User user
    IdentityFile ~/.ssh/id_ed25519

Host edge-node-3
    HostName edge-node-3.example.lan
    User user
    IdentityFile ~/.ssh/id_ed25519
```

## Privilege escalation (sudo)

`ansible/ansible.cfg` sets `become = True` globally, so Ansible runs tasks (including ad-hoc `ping`) with `sudo`. The inventory SSH user (`user`) must be able to escalate without a password prompt, or commands fail with **Missing sudo password**.

On each Pi, allow `user` to sudo without a password for automation. Create `/etc/sudoers.d/ansible` (use `visudo` so syntax is validated):

```bash
sudo visudo -f /etc/sudoers.d/ansible
```

Or use a plain editor (syntax is not validated): `sudo nano /etc/sudoers.d/ansible`

Add:

```
user ALL=(ALL) NOPASSWD: ALL
```

Save and exit. After that, `become = True` in `ansible.cfg` works without `-K` for playbooks and ad-hoc commands.

Until sudoers is configured on every host, you can pass the sudo password per run with `-K`, or skip escalation for connectivity checks only: `./bin/infra-ping -e ansible_become=false`.

## Helper scripts

Run from the repo root. All scripts use `ansible/ansible.cfg` and the fleet inventory. Names are grouped by prefix: `ansible-*` (low-level wrappers), `infra-*` (inventory, connectivity, provisioning).

| Script | Purpose |
|--------|---------|
| `bin/ansible-run` | Low-level `ansible` ad-hoc wrapper |
| `bin/ansible-playbook` | Low-level `ansible-playbook` wrapper |
| `bin/infra-list-hosts` | Show inventory host groups |
| `bin/infra-ping` | Ping all Pis (`ansible ping`) |
| `bin/infra-bootstrap` | Full bootstrap: OS update + Docker |
| `bin/infra-update-os` | OS update only (`--tags update`) |
| `bin/infra-install-packages` | Install all packages (`--tags packages`) |
| `bin/infra-install-base-packages` | Install base packages only (`--tags base_packages`) |
| `bin/infra-install-tools` | Install tools only (`--tags tools`) |
| `bin/infra-install-docker` | Docker install only (`--tags docker`) |
| `bin/infra-deploy-edge-stack` | Deploy edge stack Compose services (`--tags edge_stack`) |
| `bin/infra-docker-status` | Docker daemon, compose, uptime, and disk status |
| `bin/infra-backup-edge-stack` | Mirror edge stack data to `HA_INFRA_BACKUP` |
| `bin/infra-restore-edge-stack` | Push backup mirror to one host (`--limit` required) |
| `bin/infra-configure-firewall` | Configure UFW (`--tags firewall`) |
| `bin/infra-configure-samba` | Configure Samba public share and SMB firewall (`--tags firewall,samba`) |
| `bin/infra-reboot` | Reboot all Pis (`common` role, `--tags reboot`) |

Task helpers accept the same extra flags as Ansible (`--check`, `--limit`, `-e`, etc.).

## Fleet status and connectivity

List inventory, check SSH, and inspect Docker/system status:

```bash
./bin/infra-list-hosts
./bin/infra-ping
./bin/infra-docker-status
```

One host:

```bash
./bin/infra-ping --limit edge-node-1
./bin/infra-docker-status --limit edge-node-1
```

Until sudoers is configured on every host, ping-only checks can skip escalation: `./bin/infra-ping -e ansible_become=false`.

## Backup edge stack data

Set both required variables in gitignored `.env`:

```bash
cp .env.example .env
# HA_INFRA_CONFIG=/path/to/ha-infra-config
# HA_INFRA_BACKUP=/path/on/your/mac/for/host-mirrors
```

Install collections and tools prerequisites:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
./bin/infra-install-tools
```

Run backup:

```bash
./bin/infra-backup-edge-stack
./bin/infra-backup-edge-stack --limit edge-node-1
```

Each run refreshes `HA_INFRA_BACKUP/<inventory_hostname>/` in place (no timestamp folders). Do not commit mirrored backup data or `.env` files.

For a consistent Grafana mirror (brief downtime on database hosts), stop Grafana before rsync:

```bash
./bin/infra-backup-edge-stack -e edge_stack_backup_stop_grafana=true
```

Stale `dumps/postgresql.sql` files are removed when PostgreSQL is in the host profile but the container is not running or the dump fails.

## Restore edge stack data

Manual disaster recovery only. Bootstrap the target host first, then restore from a backup mirror.

```bash
./bin/infra-restore-edge-stack --limit edge-node-1
./bin/infra-restore-edge-stack --limit edge-node-2 -e edge_stack_restore_source=edge-node-1
```

The script refuses to run without `--limit` naming exactly one inventory host. By default it restores `data/` directories and imports `dumps/postgresql.sql`; it does not copy `.env` unless requested.

Optional flags:

```bash
# Copy mirrored .env and reconcile COMPOSE_FILE / COMPOSE_PROJECT_NAME for the target
./bin/infra-restore-edge-stack --limit edge-node-1 -e edge_stack_restore_env=true

# Keep services running during restore (default stops compose before restore)
./bin/infra-restore-edge-stack --limit edge-node-3 -e edge_stack_restore_stop_services=false
```

The playbook compares `manifest.json` services with the target `edge_stack_compose_files` profile and skips incompatible services with warnings.

## Run playbooks

The `site` playbook updates the OS, installs Docker Engine and the Docker Compose plugin, configures UFW, then deploys the edge stack (services per host profile: Mosquitto, Node-RED, PostgreSQL, Grafana).

**Dry run (no changes):**

```bash
./bin/infra-bootstrap --check
```

**Apply to the full fleet:**

```bash
./bin/infra-bootstrap
```

**Apply to one host:**

```bash
./bin/infra-bootstrap --limit edge-node-1
```

**Run only OS updates:**

```bash
./bin/infra-update-os
```

**Run only Docker installation:**

```bash
./bin/infra-install-docker
```

**Deploy edge stack only:**

```bash
./bin/infra-deploy-edge-stack
```

One host:

```bash
./bin/infra-deploy-edge-stack --limit edge-node-1
```

Dry run:

```bash
./bin/infra-deploy-edge-stack --check
```

**Configure Samba public share only:**

```bash
./bin/infra-configure-samba
```

One host:

```bash
./bin/infra-configure-samba --limit edge-node-1
```

Dry run:

```bash
./bin/infra-configure-samba --limit edge-node-1 --check
```

**Install packages:**

```bash
./bin/infra-install-packages
```

Base packages only (curl, python3):

```bash
./bin/infra-install-base-packages
```

Tools only (git, htop, mc):

```bash
./bin/infra-install-tools
```

Host lifecycle tasks (OS update, conditional reboot, on-demand reboot) live in the `common` role (`tasks/main.yml`, `tasks/reboot.yml`).

Package roles:

| Role | Purpose | Defaults |
|------|---------|----------|
| `base_packages` | Essential packages (curl, python3) | `ansible/roles/base_packages/defaults/main.yml` |
| `tools` | Admin utilities (git, htop, mc) | `ansible/roles/tools/defaults/main.yml` |
| `packages` | Meta-role; includes both (for reuse outside `site.yml`) | `ansible/roles/packages/tasks/main.yml` |
| `firewall` | UFW rules for SSH and edge stack ports | `ansible/roles/firewall/defaults/main.yml` |
| `samba` | Anonymous public SMB share at `/srv/samba/public` | `ansible/roles/samba/defaults/main.yml` |
| `edge_stack` | Deploy Compose edge stack per host profile | `ansible/roles/edge_stack/defaults/main.yml` |

Compose files live in `docker/` at the repo root. The role copies them to `/opt/docker` on each Pi.

### External config source (required)

This repository holds **templates** (`docker/`, `ansible/inventory/`). Do not deploy them to Pis.

Keep final configs in a separate clone (for example `ha-infra-config`). Set the path in a gitignored `.env` at the repo root:

```bash
cp .env.example .env
# HA_INFRA_CONFIG=/path/to/ha-infra-config
```

Expected layout in `HA_INFRA_CONFIG`:

```
ha-infra-config/
├── ansible/inventory/
│   ├── hosts.yml
│   ├── host_vars/
│   └── group_vars/          # e.g. linux_hosts.yml, linux_hosts_standby.yml
└── docker/
    ├── compose*.yml
    ├── env.example
    ├── .env                 # secrets; copied to each Pi when present
    └── data/                # mosquitto.conf, settings.js, etc.
```

Before every Ansible command (`bin/ansible-playbook`, `bin/ansible-run`, `bin/infra-list-hosts`), scripts verify that `HA_INFRA_CONFIG` is set, paths are not this repo's templates, and required `docker/` files exist.

**Deploy flow:** Ansible reads from `HA_INFRA_CONFIG`, then the `edge_stack` role **copies** those files to `/opt/docker` on each Pi (Compose files, `env.example`, optional `.env`, and data files when missing on the host). Per-host `edge_stack_compose_files` in inventory sets `COMPOSE_FILE` and `COMPOSE_PROJECT_NAME` in `/opt/docker/.env` on each run (secrets in `.env` are left unchanged). Inventory targets come from `$HA_INFRA_CONFIG/ansible/inventory/hosts.yml`.

Override per run with `-i` or `-e edge_stack_docker_dir=...` (later flags win; pre-flight still validates `HA_INFRA_CONFIG`).

Keep secrets in the external clone outside this workspace. Use `.cursorignore` in both repos.

### Edge stack credentials

Secrets are created manually on each Pi (not in Ansible vars). See [docker/README.md](../docker/README.md#credentials).

Ansible deploys `env.example`. When `docker/.env` exists on the control machine (under the repo or under `HA_INFRA_CONFIG`) it is copied to `/opt/docker/.env` on each host. Containers start only when `.env` exists on the host.

### Firewall role

| Variable | Default | Purpose |
|----------|---------|---------|
| `firewall_enabled` | `true` | Enable UFW |
| `firewall_trusted_cidrs` | RFC1918 ranges | Sources allowed to reach trusted service ports |
| `firewall_edge_ports` | `1880`, `1883` | Edge stack ports |
| `firewall_samba_enabled` | `samba_enabled` | Toggle SMB firewall rules |
| `firewall_samba_ports` | `445` | Samba SMB ports |

Restrict further per site with `host_vars` if needed (for example a single `/24`).

### Samba public share

The `samba` role configures a guest read-write share on active hosts using inventory defaults from `group_vars/linux_hosts.yml`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `samba_enabled` | `false` (role default) | Enable Samba role |
| `samba_share_name` | `public` | Share name for SMB clients |
| `samba_share_path` | `/srv/samba/public` | Shared directory path |
| `samba_share_directory_mode` | `"0777"` | World read-write permissions for anonymous access |

Guest mode is intentionally open to trusted LAN clients only. Keep `firewall_trusted_cidrs` restricted to your internal networks and do not expose SMB to the public internet.

Mount examples:

```bash
# macOS
mount -t smbfs //guest@edge-node-1.example.lan/public /tmp/samba-public

# Linux
sudo mount -t cifs //edge-node-1.example.lan/public /mnt/samba-public -o guest,uid=$(id -u),gid=$(id -g)
```

### Mosquitto migration

If a Pi already has an anonymous `mosquitto.conf` from an earlier deploy, Ansible will not overwrite it. Replace it manually or delete `data/mosquitto/config/mosquitto.conf` and re-run `./bin/infra-deploy-edge-stack`.

**Reboot the fleet:**

```bash
./bin/infra-reboot
```

One host:

```bash
./bin/infra-reboot --limit edge-node-1
```

**Reboot after upgrade when required** (off by default):

```bash
./bin/infra-update-os -e reboot_after_upgrade=true
```

## Verify Docker

After the playbook completes, on each Pi:

```bash
ssh edge-node-1 docker --version
ssh edge-node-1 docker compose version
```

The `user` account is added to the `docker` group. Log out and back in (or open a new SSH session) before running `docker` without `sudo`.
