# Edge stack (Docker Compose)

Autonomous sites run Node-RED, Mosquitto, and a mounted SQLite automation database.
The home site may additionally run PostgreSQL and Grafana as a central history tier.
Deployed by the Ansible `edge_stack` role to `/opt/docker` on each host.

## Site profiles

| Profile | Services | Template host | Purpose |
|---------|----------|---------------|---------|
| **Autonomous site** | Node-RED, Mosquitto, SQLite mount | edge-node-2 | Local automation per site |
| **Home history tier** | PostgreSQL, Grafana | edge-node-3 | Central telemetry/events and dashboards |
| **Full lab** | All services | edge-node-1 | Development / integration testing |

SQLite is **not** a Compose service. It is a file bind-mounted into Node-RED:

- **Host path:** `${DOCKER_PATH}/data/sqlite/automation.db` (default `/opt/docker/data/sqlite/automation.db`)
- **Container path:** `/data/sqlite/automation.db`

## Services

| Service | Port | Profile | Purpose |
|---------|------|---------|---------|
| Node-RED | 1880 | Autonomous site | Flow editor and runtime |
| Mosquitto | 1883, 9001 | Autonomous site | MQTT broker (9001 = WebSockets) |
| SQLite (`automation.db`) | — | Autonomous site | Per-site automation database (file mount) |
| PostgreSQL | 5432 | Home history tier | Central history database |
| Grafana | 3000 | Home history tier | Dashboards |
| Portainer | 9443 | Optional (lab) | Docker management UI |

`edge-node-1` runs the full lab stack. `edge-node-2` is the autonomous-site template.
`edge-node-3` is the home history tier template. See per-host `edge_stack_compose_files`
in `ansible/inventory/host_vars/`.

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
    ├── mosquitto/config/     # mosquitto.conf, passwords_file (manual)
    └── sqlite/               # automation.db starter (mounted into Node-RED at /data/sqlite)
```

Node-RED mounts `${DOCKER_PATH}/data/sqlite` at `/data/sqlite`. Path inside the container: `/data/sqlite/automation.db`. This is the per-site automation database (catalog, snapshots, short-retention telemetry/events). See [ha-apps database docs](https://github.com/luismiguelbp/ha-apps/blob/main/docs/database/automation.md).

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
