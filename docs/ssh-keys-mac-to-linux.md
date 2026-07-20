# SSH Keys: Mac to Linux

Key-based SSH from your Mac to Linux servers. Hostnames and SSH user come from [ansible/inventory/](../ansible/inventory/) (production names live in `HA_INFRA_CONFIG`).

## Generate key (Mac)

Skip if you already have a key pair.

```bash
ssh-keygen -t ed25519 -C "mac-to-linux"
# default: ~/.ssh/id_ed25519 (+ .pub)
```

## Copy public key to each server

Template example (`user` is the inventory SSH user):

```bash
ssh-copy-id user@edge-node-1.example.lan
```

Repeat for every host in your inventory. On macOS without `ssh-copy-id`: `brew install ssh-copy-id`.

Manual fallback:

```bash
cat ~/.ssh/id_ed25519.pub | ssh user@edge-node-1.example.lan "mkdir -p ~/.ssh; chmod 700 ~/.ssh; cat >> ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys"
```

## Test

```bash
ssh user@edge-node-1.example.lan
```

## Optional: `~/.ssh/config`

One block per host (`chmod 600 ~/.ssh/config`):

```ssh-config
Host edge-node-1
    HostName edge-node-1.example.lan
    User user
    IdentityFile ~/.ssh/id_ed25519
```

Then: `ssh edge-node-1`

## Optional: disable password login (server)

After key login works on every host — edit `/etc/ssh/sshd_config`:

```text
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH (`ssh` on Debian/Ubuntu; `sshd` on RHEL/Fedora). Keep the current session open while testing a new connection.

## Troubleshooting

**Permission denied** on the server:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## Next step

[Ansible fleet setup](ansible.md) — passwordless `sudo` for the SSH user is required there.
