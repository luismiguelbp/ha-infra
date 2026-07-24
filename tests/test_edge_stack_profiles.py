"""Contract tests for template edge stack host profiles."""

from pathlib import Path

import yaml

from contract_helpers import TEMPLATE_HOST_VARS_DIR

AUTONOMOUS_SITE_COMPOSE = {
    "compose.yml",
    "compose-node-red.yml",
    "compose-mosquitto.yml",
}
HISTORY_TIER_COMPOSE = {
    "compose.yml",
    "compose-postgresql.yml",
    "compose-grafana.yml",
}
FULL_LAB_COMPOSE = AUTONOMOUS_SITE_COMPOSE | HISTORY_TIER_COMPOSE | {"compose-portainer.yml"}


def _load_host_vars(hostname: str) -> dict:
    path = TEMPLATE_HOST_VARS_DIR / f"{hostname}.yml"
    return yaml.safe_load(path.read_text())


def test_edge_node_2_autonomous_site_profile() -> None:
    """edge-node-2 runs MQTT edge with SQLite and no central history services."""
    host_vars = _load_host_vars("edge-node-2")
    compose = set(host_vars["edge_stack_compose_files"])
    data_dirs = set(host_vars["edge_stack_data_dirs"])

    assert compose == AUTONOMOUS_SITE_COMPOSE
    assert "data/sqlite" in data_dirs
    assert "data/catalog" in data_dirs
    assert "compose-postgresql.yml" not in compose
    assert "compose-grafana.yml" not in compose
    assert "edge_stack_data_files" not in host_vars


def test_edge_node_3_home_history_tier_profile() -> None:
    """edge-node-3 runs PostgreSQL + Grafana only and skips seed file copy."""
    host_vars = _load_host_vars("edge-node-3")
    compose = set(host_vars["edge_stack_compose_files"])
    data_dirs = set(host_vars.get("edge_stack_data_dirs", []))

    assert compose == HISTORY_TIER_COMPOSE
    assert host_vars.get("edge_stack_data_files") == []
    assert "compose-node-red.yml" not in compose
    assert "compose-mosquitto.yml" not in compose
    assert "data/sqlite" not in data_dirs


def test_edge_node_1_full_lab_superset() -> None:
    """edge-node-1 includes every autonomous-site and history-tier service."""
    host_vars = _load_host_vars("edge-node-1")
    compose = set(host_vars["edge_stack_compose_files"])
    data_dirs = set(host_vars["edge_stack_data_dirs"])

    assert compose == FULL_LAB_COMPOSE
    assert AUTONOMOUS_SITE_COMPOSE.issubset(compose)
    assert HISTORY_TIER_COMPOSE.issubset(compose)
    assert "data/sqlite" in data_dirs
    assert "data/catalog" in data_dirs


def test_data_dirs_align_with_compose_services() -> None:
    """Each template host creates data dirs for its compose profile."""
    expectations: dict[str, list[tuple[str, str]]] = {
        "edge-node-1": [
            ("compose-portainer.yml", "data/portainer"),
            ("compose-node-red.yml", "data/node-red/data"),
            ("compose-mosquitto.yml", "data/mosquitto/config"),
            ("compose-node-red.yml", "data/catalog"),
            ("compose-node-red.yml", "data/sqlite"),
            ("compose-postgresql.yml", "data/postgresql/data"),
            ("compose-grafana.yml", "data/grafana/data"),
        ],
        "edge-node-2": [
            ("compose-node-red.yml", "data/node-red/data"),
            ("compose-mosquitto.yml", "data/mosquitto/config"),
            ("compose-node-red.yml", "data/catalog"),
            ("compose-node-red.yml", "data/sqlite"),
        ],
        "edge-node-3": [
            ("compose-postgresql.yml", "data/postgresql/data"),
            ("compose-grafana.yml", "data/grafana/data"),
        ],
    }

    for hostname, pairs in expectations.items():
        host_vars = _load_host_vars(hostname)
        compose = set(host_vars["edge_stack_compose_files"])
        data_dirs = set(host_vars.get("edge_stack_data_dirs", []))
        for compose_file, data_dir in pairs:
            assert compose_file in compose, f"{hostname}: missing {compose_file}"
            assert data_dir in data_dirs, f"{hostname}: missing {data_dir}"
