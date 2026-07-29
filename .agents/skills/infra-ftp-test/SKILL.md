---
name: infra-ftp-test
description: FTP/FTPS connectivity and read/write checks for ha-infra hosts. Use when running infra-ftp-test, HA_INFRA_FTP_HOST, HA_INFRA_FTP_TLS, HA_INFRA_FTP_USER, HA_INFRA_FTP_PASSWORD, or troubleshooting FTP login and share access.
disable-model-invocation: true
---

# Infra FTP test

Test FTP or explicit FTPS against a fleet host from the control machine. Credentials come from OS environment variables (or gitignored `.env` loaded by the wrapper).

## When to use

- FTP/FTPS login or connectivity failures
- Verify read/write on the shared public share
- Troubleshoot after `./bin/infra-configure-ftp`

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `HA_INFRA_FTP_HOST` | yes | FTP hostname (e.g. `edge-node-1.example.lan`) |
| `HA_INFRA_FTP_USER` | yes | FTP username |
| `HA_INFRA_FTP_PASSWORD` | yes | FTP password |
| `HA_INFRA_FTP_PORT` | no | Default `21` |
| `HA_INFRA_FTP_TLS` | no | Set `1` / `true` for explicit FTPS (AUTH TLS) |
| `HA_INFRA_FTP_TLS_INSECURE` | no | Set `1` / `true` to accept self-signed certificates |

Set in shell or gitignored `.env` at the ha-infra repo root. Never print or commit passwords.

## Workflow

1. Confirm required env vars are set (report missing names only, not values).
2. Status check:

```bash
./bin/infra-ftp-test status
```

FTPS (self-signed):

```bash
export HA_INFRA_FTP_TLS=1
export HA_INFRA_FTP_TLS_INSECURE=1
./bin/infra-ftp-test status
```

3. Write probe (upload then delete unless `--keep`):

```bash
./bin/infra-ftp-test write
./bin/infra-ftp-test write --keep
```

4. Read a remote file:

```bash
./bin/infra-ftp-test read --remote .ha-infra-ftp-probe-<timestamp>.txt
```

## Troubleshooting

- **Connection refused**: `ftp_enabled` false, vsftpd not running, or firewall blocking TCP 21 / passive ports 40000-40009
- **Login failed**: wrong `HA_INFRA_FTP_*` credentials, user not in `ftp_users`, or FTP shell missing from `/etc/shells` (role adds `ftp_user_shell`)
- **TLS handshake / certificate errors**: set `HA_INFRA_FTP_TLS=1`; for self-signed also `HA_INFRA_FTP_TLS_INSECURE=1`. Confirm `ftp_tls_enabled: true` on the host
- **530 SSL required**: host has `ftp_tls_force: true` — plain FTP will fail; use FTPS
- **Passive mode errors**: UFW must allow `40000:40009` from client network (`firewall_trusted_cidrs`)
- **Host health**: use `infra-status` for ping and Docker; FTP is a host package, not Compose
- **Journal clue**: `pam_shells(vsftpd:auth): User has an invalid shell` means redeploy so `/usr/sbin/nologin` is in `/etc/shells`

## Related skills

- `infra-ftp`: deploy and configure vsftpd
- `infra-status`: fleet connectivity and Docker checks

## Reference

- Helper script: `scripts/infra_ftp_test.py`
- Docs: `docs/ansible.md` (FTP share section)
