---
name: infra-deploy
description: Run the managed-infra full fleet bootstrap workflow. Use when the user asks to deploy, bootstrap, provision, or run infra-bootstrap for all hosts or a single host.
disable-model-invocation: true
---

# Infra Deploy

Run a full fleet bootstrap on all configured Linux hosts, or on one host when a hostname is passed. Template example: `/infra-deploy edge-node-1`.

Uses `./bin/infra-bootstrap` from the managed-infra repo root.

## Host parameter

- No parameter: deploy all hosts in inventory.
- One hostname: add `--limit <hostname>` using the inventory name from `./bin/infra-list-hosts`, not DNS.

Examples in this repo use template names (`edge-node-1`, `edge-node-2`, `edge-node-3`). Live inventory comes from `MANAGED_INFRA_CONFIG`; see `AGENTS.md`.

## Steps

1. Confirm the repo root and read `AGENTS.md` for the two-repo and templates-only rules.
2. List hosts with `./bin/infra-list-hosts`.
3. Ping with `./bin/infra-ping` or `./bin/infra-ping --limit <host>`.
4. Deploy with `./bin/infra-bootstrap` or `./bin/infra-bootstrap --limit <host>`.
5. Verify with `./bin/infra-docker-status`. Add `--limit <host>` when scoped to one host.

## Rules

- Do not read or print secrets from `MANAGED_INFRA_CONFIG`.
- If ping fails, stop and report; do not run bootstrap.
- For Compose-only updates after initial bootstrap, suggest `./bin/infra-deploy-edge-stack` instead.

## Output

Summarize hosts targeted, bootstrap result, and container status per host.
