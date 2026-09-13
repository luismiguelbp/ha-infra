# ha-infra Agent Guide

This repository contains infrastructure-as-code templates for a small Linux fleet. It is safe to edit templates here, but production inventory, secrets, and tuned configs live outside this repository.

**Storage model:** autonomous sites run Node-RED + Mosquitto + deployed `catalog.json` + mounted SQLite (`data/sqlite/automation.db`). The home site may run PostgreSQL + Grafana as a central history tier. SQLite is a file mount, not a Compose service. PostgreSQL and Grafana are not required on every host.

- Read the [README](README.md) for setup, layout, and documentation.
- Read relevant documentation ([docs/ansible.md](docs/ansible.md), [docker/README.md](docker/README.md)) before changing infrastructure behavior.
- Discover skills under [`.agents/skills/`](.agents/skills/) and read the matching `SKILL.md` when the task fits. Do not load unused skills.
- Portable Agent Skills live in `.agents/skills/`; Cursor-specific behavior belongs in `.cursor/rules/` only when needed.

## Engineering Principles

- **KISS — Keep It Simple:** choose the simplest solution that meets the requirements.
- **LEAN:** minimize waste—code, dependencies, steps, and work that add no value.
- **YAGNI — You Aren’t Gonna Need It:** don’t implement features or abstractions until they’re actually needed.
- **DRY — Don’t Repeat Yourself:** keep a single source of truth; link instead of copying.

## Conventional Commits

- Commits: `<type>: <short imperative summary>` (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`).

## Templates Only

This repository is **IaC templates**, not production config. Ansible and Docker files here are **not deployed as-is**.

Use fictional names from `ansible/inventory/` in docs, rules, skills, commands, comments, and examples:

| Use | Examples |
|-----|----------|
| Inventory hosts | `edge-node-1`, `edge-node-2`, `edge-node-3` |
| Sites / locations | `site-a`, `site-b`, `site-c` |
| DNS | `edge-node-1.example.lan`, `edge-node-2.example.lan`, `edge-node-3.example.lan` |

Do **not** add real hostnames, real DNS names, real locations, or fleet-specific paths to this repository.

That includes **service aliases and secondary DNS names** (for example MQTT broker hostnames or CNAME targets). In this repo use only the fictional `edge-node-N.example.lan` names from the table above, or Compose service names such as `mosquitto` where appropriate.

### Runtime vs committed content

| Context | Names to use |
|---------|----------------|
| Committed files in `ha-infra` (docs, README, tests, comments, examples) | Fictional template names only |
| Live fleet operations (`HA_INFRA_CONFIG`, Ansible, SSH, status checks) | Production inventory from the external config clone |
| Chat or investigation summaries | Production names are fine when reporting status; **sanitize before writing to this repo** |

When troubleshooting on production hosts, do not paste discovered hostnames, DNS aliases, or IPs into files that will be committed here. Translate examples to `edge-node-N.example.lan` and `site-a` / `site-b` / `site-c`.

## Two-Repo Model

| Repo | Role |
|------|------|
| `ha-infra` | Playbooks, roles, templates, wrapper scripts, and example inventory |
| External config clone | Real inventory, secrets, production Compose files, and tuned data files |

Production inventory, secrets, credential hashes, and tuned service configs belong in `HA_INFRA_CONFIG`, which is configured through the gitignored `.env` file.

When **writing or editing files in this repo**, always use the fictional template names above. When **running deploy commands**, host names come from the live inventory under `HA_INFRA_CONFIG`.

## Security Rules

- Never read, print, echo, commit, or summarize secrets from `.env`, `passwords_file`, credential hashes, or production config files.
- Do not commit backup data, mirrored `.env` files, or runtime service data.
- Keep real host metadata in the external config clone only.
- Keep secret patterns aligned in `.gitignore` and `.cursorignore`.
- If a task requires secret values, ask the user to run the sensitive step locally or confirm only non-secret status.

## Verification

Run from the `ha-infra` repo root. Setup and script usage live in the [README](README.md) and [docs/ansible.md](docs/ansible.md); task workflows live in the matching skill.

```bash
pytest
./bin/infra-list-hosts
./bin/infra-ping
```

`pytest` includes a guard that fails if non-fictional `*.lan` hostnames appear in committed template files (only `*.example.lan` is allowed).

## Operational Guardrails

- Prefer `--limit edge-node-1` or another single host for first production runs or risky changes.
- Run `./bin/infra-list-hosts` before fleet operations so the target set is clear.
- Run `./bin/infra-ping` before deploy, backup, restore, or reboot operations.
- If ping fails, stop and report the failure before running disruptive commands.
- Do not reboot more than one host without confirming the target host list with the user.
- Restores are manual disaster recovery operations and require exactly one target host via `--limit`.
- Compose-only updates should use `./bin/infra-deploy-edge-stack` instead of full bootstrap.

## References

- `README.md`: repository overview, setup, and helper scripts
- `docs/ansible.md`: inventory, helper scripts, limits, and options
- `docker/README.md`: edge stack layout and credential handling
- `ansible/inventory/`: fictional template inventory
