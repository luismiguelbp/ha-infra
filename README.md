# ha-infra

Infrastructure-as-code for a small Raspberry Pi fleet. Ansible and Docker Compose on the devices; wrapper scripts on your Mac.

## Contents

- Getting started (first-time fleet setup): below
- SSH keys (Mac to Pi): [docs/ssh-keys-mac-to-linux.md](docs/ssh-keys-mac-to-linux.md)
- Ansible inventory and `site` playbook: [docs/ansible.md](docs/ansible.md)
- Edge stack (Compose services per host profile): [docker/README.md](docker/README.md)
- Helper scripts in `bin/` (`ansible-*`, `infra-*` prefixes)

## Getting started

First-time setup on your Mac, in order:

1. [SSH keys to each Pi](docs/ssh-keys-mac-to-linux.md)
2. [Passwordless sudo](docs/ansible.md#privilege-escalation-sudo) for the inventory SSH user on every host
3. [Setup](#setup) — venv, dependencies, and `HA_INFRA_CONFIG` in `.env`
4. Ansible collections (once): `ansible-galaxy collection install -r ansible/requirements.yml`
5. Bootstrap: `./bin/infra-bootstrap --check`, then `./bin/infra-bootstrap`
6. [Edge stack credentials](docker/README.md#credentials) on each Pi, then `./bin/infra-docker-status`

Day-to-day commands and options: [docs/ansible.md](docs/ansible.md).

## Prerequisites

- Python 3.10+ (for contract tests)
- Ansible on the control machine (`brew install ansible`)
- SSH key access to each Pi — [docs/ssh-keys-mac-to-linux.md](docs/ssh-keys-mac-to-linux.md)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # required: set HA_INFRA_CONFIG (external clone with real docker/ configs)
# optional for backups: set HA_INFRA_BACKUP (local mirror root on your Mac)
```

## Test

```bash
pytest
```

## Ansible (fleet bootstrap)

```bash
./bin/infra-list-hosts
./bin/infra-ping
./bin/infra-bootstrap --check
./bin/infra-bootstrap
./bin/infra-deploy-edge-stack
./bin/infra-configure-samba
./bin/infra-configure-ftp
./bin/infra-ftp-test status
./bin/infra-docker-status
./bin/infra-backup-edge-stack
```

See [docs/ansible.md](docs/ansible.md) for all helper scripts, limits, and options.

Install Ansible collections once: `ansible-galaxy collection install -r ansible/requirements.yml`

Edge stack credentials are set manually on each Pi. See [docker/README.md](docker/README.md#credentials).

## Workflow

1. Develop playbooks and **templates** in this repo (`docker/`, `ansible/inventory/` are not deployed as-is).
2. Maintain final configs (hosts, secrets, tuned `mosquitto.conf`, etc.) in `HA_INFRA_CONFIG` (see `.env.example`).
3. Run `bin/` helpers — they verify the external paths, then Ansible copies `docker/` files to `/opt/docker` on each Pi.

## AI agent context

- `AGENTS.md` contains portable project guidance for Codex and other AI coding agents.
- `.agents/skills/` contains standard Agent Skills for fleet operations and command-like workflows.
- `.cursor/rules/` remains available only for Cursor-specific rule behavior.
