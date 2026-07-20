# Edge stack (Docker Compose)

Node-RED and Mosquitto on MQTT edge nodes; Portainer, PostgreSQL, and Grafana on full-stack or metrics nodes. Deployed by the Ansible `edge_stack` role to `/opt/docker` on each host.

## Services

| Service | Port | Hosts | Purpose |
|---------|------|-------|---------|
| Portainer | 9443 | edge-node-1 | Docker management UI |
| Node-RED | 1880 | edge-node-1, edge-node-2 | Flow editor and runtime |
| Mosquitto | 1883, 9001 | edge-node-1, edge-node-2 | MQTT broker (9001 = WebSockets) |
| PostgreSQL | 5432 | edge-node-1, edge-node-3 | Database (Grafana backend) |
| Grafana | 3000 | edge-node-1, edge-node-3 | Dashboards |

`edge-node-1` runs the full stack (lab template). `edge-node-2` is MQTT-only. `edge-node-3` is database / metrics only. See per-host `edge_stack_compose_files` in `ansible/inventory/host_vars/`.

## Layout

Repository (`docker/`) mirrors `/opt/docker/` on each Pi. Runtime data (flows, Mosquitto persistence) lives on the Pi only.

```
docker/
├── compose*.yml
├── env.example
├── .env                      # gitignored; copied to Pi when present
└── data/
    ├── portainer/            # Portainer state
    ├── node-red/data/        # settings.js starter
    └── mosquitto/config/     # mosquitto.conf, passwords_file (manual)
```

## Credentials

Secrets stay on each Pi (or in gitignored `docker/.env` on your Mac). Run once per Pi, or again after wiping `/opt/docker`.

**1. Environment file**

Create `docker/.env` locally and deploy with `./bin/infra-deploy-edge-stack`, or on the Pi:

```bash
cp /opt/docker/env.example /opt/docker/.env
```

Set `NODE_RED_CREDENTIAL_SECRET`, `MQTT_USER`, and `MQTT_PASSWORD` in `.env`. Generate the password with `openssl rand -hex 32`. See `env.example`.

**2. Mosquitto user**

On the Pi (`cd /opt/docker`), create the single MQTT user (same values as `MQTT_USER` / `MQTT_PASSWORD` in `.env`):

```bash
docker run --rm -v "$PWD/data/mosquitto/config:/mosquitto/config" \
  eclipse-mosquitto:latest mosquitto_passwd -c -b /mosquitto/config/passwords_file YOUR_MQTT_USER YOUR_MQTT_PASSWORD
```

Node-RED and the Mosquitto healthcheck both use this user.

**3. Node-RED editor login**

Edit `data/node-red/data/settings.js` on the Pi. Generate a bcrypt hash:

```bash
docker run --rm nodered/node-red:latest \
  node -e "console.log(require('bcryptjs').hashSync('YOUR_ADMIN_PASSWORD', 8))"
```

Replace `$2b$08$REPLACE_WITH_BCRYPT_HASH` in `settings.js`, then `docker compose restart node-red`.

Containers start only when `/opt/docker/.env` exists. Ansible does not overwrite existing `passwords_file`, `mosquitto.conf`, or customized `settings.js`.

## Node-RED

- MQTT broker: `mosquitto:1883`, user/password from `MQTT_USER` / `MQTT_PASSWORD` in `.env`
- Use the Compose service name `mosquitto` when Node-RED runs in the same stack. Secondary LAN names (for example a CNAME alias when the canonical A record is `edge-node-1.example.lan`) often fail to resolve inside the Node-RED container (Node-RED stays on **connecting**). For remote brokers, use the inventory `dns_name` (for example `edge-node-2.example.lan`) or the host IP.
- Port `8883` is not published until TLS is enabled in `mosquitto.conf`; use plain MQTT on `1883` or WebSockets on `9001`.
- Credential encryption: `NODE_RED_CREDENTIAL_SECRET` in `.env` (read by `settings.js` as `credentialSecret`)
- Editor login: user `admin` in `settings.js`

## Images

| Service | Image |
|---------|-------|
| Portainer | `portainer/portainer-ce:latest` |
| Node-RED | `nodered/node-red:latest` |
| Mosquitto | `eclipse-mosquitto:latest` |
| PostgreSQL | `postgres:16-alpine` |
| Grafana | `grafana/grafana:latest` |

## Commands

On a Pi:

```bash
cd /opt/docker
docker compose ps
docker compose logs -f mosquitto
docker compose restart node-red
```

From your Mac:

```bash
./bin/infra-deploy-edge-stack
./bin/infra-deploy-edge-stack --limit edge-node-1
./bin/infra-deploy-edge-stack --check
```

See [docs/ansible.md](../docs/ansible.md) for Ansible prerequisites and helper scripts.
