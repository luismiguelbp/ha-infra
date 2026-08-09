---
name: infra-ftp
description: Configure and deploy FTP/FTPS (vsftpd) on ha-infra fleet hosts. Use when enabling ftp_enabled, ftp_tls_enabled, ftp_users in HA_INFRA_CONFIG, or running infra-configure-ftp for the shared Samba public share.
disable-model-invocation: true
---

# Infra FTP

Configure authenticated FTP (optional explicit FTPS) on fleet hosts that share `/srv/samba/public` with the Samba public share.

## When to use

- Enable or update vsftpd on a host
- Set `ftp_enabled`, optional `ftp_tls_enabled`, and `ftp_users` in `HA_INFRA_CONFIG` inventory
- Run `./bin/infra-configure-ftp`

## Prerequisites

- `HA_INFRA_CONFIG` set in gitignored `.env`
- Host in inventory with `ftp_enabled: true` and at least one `ftp_users` entry
- Samba share path already present or created by the FTP role (`/srv/samba/public`)

## Steps

1. Confirm repo root and list hosts: `./bin/infra-list-hosts`
2. In `HA_INFRA_CONFIG`, set per host or group vars (use ansible-vault for passwords):

```yaml
ftp_enabled: true
ftp_tls_enabled: true
ftp_users:
  - name: ftpuser
    password: "vault-or-secret"
```

Leave `ftp_tls_cert_src` / `ftp_tls_key_src` empty to generate a self-signed cert on the host (CN from `dns_name` when set).

3. Deploy FTP and refresh firewall rules:

```bash
./bin/infra-configure-ftp --limit edge-node-1
./bin/infra-configure-ftp --limit edge-node-1 --check
```

4. Verify with the `infra-ftp-test` skill (`HA_INFRA_FTP_TLS_INSECURE=1` for self-signed).

## Rules

- Do not read, echo, or commit passwords or private keys from vault, host_vars, or production config
- Use fictional names only in this repo (`edge-node-1.example.lan`, `ftpuser` in examples)
- Prefer FTPS (`ftp_tls_enabled: true`); keep `firewall_trusted_cidrs` restricted

## Reference

- Role defaults: `ansible/roles/ftp/defaults/main.yml`
- Firewall ports: TCP 21 and passive range 40000-40009 from `firewall_trusted_cidrs`
- Full script table: `docs/ansible.md`
