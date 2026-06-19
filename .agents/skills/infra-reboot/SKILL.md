---
name: infra-reboot
description: Reboot all managed-infra Linux hosts or one limited host using the infra-reboot helper.
disable-model-invocation: true
---

# Infra Reboot

Reboot all configured Linux hosts, or one host when a hostname is passed. Template example: `/infra-reboot edge-node-2`.

Uses `./bin/infra-reboot`.

## Host parameter

- No parameter: reboot all hosts in inventory.
- One hostname: add `--limit <hostname>` using the inventory name from `./bin/infra-list-hosts`, not DNS.

Examples in this repo use template names (`edge-node-1`, `edge-node-2`, `edge-node-3`). Live inventory comes from `MANAGED_INFRA_CONFIG`; see `AGENTS.md`.

## Steps

1. Confirm the repo root.
2. List hosts with `./bin/infra-list-hosts`.
3. Ping with `./bin/infra-ping` or `./bin/infra-ping --limit <host>`.
4. Confirm targets with the user when more than one host would reboot.
5. Reboot with `./bin/infra-reboot` or `./bin/infra-reboot --limit <host>`.
6. Wait about 60 seconds, then verify with `./bin/infra-ping` on the same scope.

## Rules

- Do not reboot without confirming the target host list with the user when more than one host is affected.
- If ping fails after reboot, wait and retry once before reporting failure.

## Output

Summarize hosts rebooted, ping result after recovery, and any failures.
