---
name: infra-ftp-test
description: FTP/FTPS connectivity and read/write checks for ha-infra hosts. Use when running infra-ftp-test --limit, HA_INFRA_FTP_USER, HA_INFRA_FTP_PASS, HA_INFRA_FTP_TLS_INSECURE, or troubleshooting FTP login and share access.
disable-model-invocation: true
---

# Infra FTP test

Test FTP or explicit FTPS against one fleet host from the control machine.

Hostname comes from inventory `host_vars` `dns_name` (fallback `ansible_host`). TLS follows `ftp_tls_enabled`. Credentials stay in the OS environment.

## When to use

- FTP/FTPS login or connectivity failures
- Verify read/write on the shared public share
- Troubleshoot after `./bin/infra-configure-ftp`

## Prerequisites

- `HA_INFRA_CONFIG` set in gitignored `.env`
- Host has `ftp_enabled: true` in inventory
- OS env `HA_INFRA_FTP_USER` / `HA_INFRA_FTP_PASS`

## Environment variables

| Variable | Required | Where | Purpose |
|----------|----------|-------|---------|
| `HA_INFRA_CONFIG` | yes | `.env` | External inventory root |
| `HA_INFRA_FTP_USER` | yes | OS env | FTP username |
| `HA_INFRA_FTP_PASS` | yes | OS env | FTP password |
| `HA_INFRA_FTP_PORT` | no | `.env` / OS | Default `21` |
| `HA_INFRA_FTP_TLS_INSECURE` | no | `.env` / OS | Accept self-signed certificates |

Never print or commit passwords. Do not set a separate FTP hostname env var — use `--limit`.

## Workflow

1. Confirm inventory host: `./bin/infra-list-hosts`
2. Status check:

```bash
./bin/infra-ftp-test --limit edge-node-1 status
```

Self-signed FTPS (typical after `infra-configure-ftp`):

```bash
export HA_INFRA_FTP_TLS_INSECURE=1
./bin/infra-ftp-test --limit edge-node-1 status
```

3. Write probe (upload then delete unless `--keep`):

```bash
./bin/infra-ftp-test --limit edge-node-1 write
./bin/infra-ftp-test --limit edge-node-1 write --keep
```

4. Read a remote file:

```bash
./bin/infra-ftp-test --limit edge-node-1 read --remote .ha-infra-ftp-probe-<timestamp>.txt
```

## Troubleshooting

- **Configuration error / unknown host**: check `--limit` against `./bin/infra-list-hosts`
- **ftp_enabled is false**: enable FTP in `host_vars` and run `./bin/infra-configure-ftp --limit <host>`
- **Connection refused**: vsftpd not running, or firewall blocking TCP 21 / passive ports 40000-40009
- **Login failed**: wrong `HA_INFRA_FTP_USER` / `HA_INFRA_FTP_PASS`, user not in `ftp_users`, or FTP shell missing from `/etc/shells`
- **TLS handshake / certificate errors**: set `HA_INFRA_FTP_TLS_INSECURE=1` for self-signed; confirm `ftp_tls_enabled: true` on the host
- **530 SSL required**: host has `ftp_tls_force: true` — plain FTP will fail; use FTPS
- **Passive mode errors**: UFW must allow `40000:40009` from client network (`firewall_trusted_cidrs`)
- **Journal clue**: `pam_shells(vsftpd:auth): User has an invalid shell` means redeploy so `/usr/sbin/nologin` is in `/etc/shells`

## Related skills

- `infra-ftp`: deploy and configure vsftpd
- `infra-status`: fleet connectivity and Docker checks

## Reference

- Helper scripts: `scripts/infra_ftp_test.py`, `scripts/infra_inventory.py`
- Docs: `docs/ansible.md` (FTP share section)
