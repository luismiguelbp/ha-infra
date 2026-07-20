---
name: infra-status
description: Check ha-infra fleet health, Docker daemon state, Compose status, uptime, and disk usage for all hosts or a single host.
disable-model-invocation: true
---

# Infra Status

Check fleet health on all configured Linux hosts, or on one host when a hostname is passed. Template example: `/infra-status edge-node-1`.

## Host parameter

- No parameter: status for all hosts in inventory.
- One hostname: add `--limit <hostname>` using the inventory name from `./bin/infra-list-hosts`, not DNS.

Examples in this repo use template names (`edge-node-1`, `edge-node-2`, `edge-node-3`). Live inventory comes from `HA_INFRA_CONFIG`; see `AGENTS.md`.

## Steps

1. Confirm the repo root.
2. List hosts with `./bin/infra-list-hosts`.
3. Ping with `./bin/infra-ping` or `./bin/infra-ping --limit <host>`.
4. Check Docker and system status with `./bin/infra-docker-status` or `./bin/infra-docker-status --limit <host>`.

## Rules

- Do not read or print secrets from `HA_INFRA_CONFIG`.
- If ping fails for a host, report it separately from container status.

## Output

For each host, summarize ping result, Docker daemon state, edge stack presence, container names/status/health, Compose version, uptime, root disk usage, and edge stack path disk usage.
