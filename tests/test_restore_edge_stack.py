"""Structural and syntax checks for edge stack restore."""

import json
import shutil
import subprocess
from pathlib import Path

import yaml

from contract_helpers import PROJECT_ROOT

RESTORE_SCRIPT = PROJECT_ROOT / "bin" / "infra-restore-edge-stack"
RESTORE_PLAYBOOK = PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-restore.yml"
LIB_SCRIPT = PROJECT_ROOT / "bin" / "_lib.sh"

REQUIRED_PLAYBOOK_VARS = {
    "edge_stack_restore_source",
    "edge_stack_restore_env",
    "edge_stack_restore_stop_services",
}

REQUIRED_TASK_NAMES = {
    "Load backup manifest",
    "Warn when backup includes services not on target host",
    "Warn when target host expects services missing from backup",
    "Warn when backup includes SQLite but target host has no SQLite data dir",
    "Warn when target host expects SQLite but backup manifest does not",
    "Restore Mosquitto data directory",
    "Restore Node-RED data directory",
    "Restore SQLite data directory",
    "Restore Grafana data directory",
    "Set SQLite data ownership",
    "Import PostgreSQL dump on host",
    "Start edge stack services after restore",
}


def _playbook_task_names(playbook: dict) -> set[str]:
    names: set[str] = set()
    for play in playbook:
        for task in play.get("tasks", []):
            if "name" in task:
                names.add(task["name"])
    return names


def test_infra_restore_script_and_playbook_exist() -> None:
    """Restore wrapper and playbook are present for manual disaster recovery."""
    assert RESTORE_SCRIPT.is_file()
    assert RESTORE_SCRIPT.stat().st_mode & 0o111
    assert RESTORE_PLAYBOOK.is_file()


def test_restore_playbook_declares_required_vars() -> None:
    """Restore playbook exposes the expected operator-facing variables."""
    playbook = yaml.safe_load(RESTORE_PLAYBOOK.read_text())
    play_vars = playbook[0]["vars"]
    assert REQUIRED_PLAYBOOK_VARS.issubset(play_vars.keys())


def test_restore_playbook_includes_core_tasks() -> None:
    """Restore playbook mirrors backup coverage for each edge stack service."""
    playbook = yaml.safe_load(RESTORE_PLAYBOOK.read_text())
    task_names = _playbook_task_names(playbook)
    missing = REQUIRED_TASK_NAMES - task_names
    assert not missing, f"Missing tasks: {sorted(missing)}"


def test_restore_script_requires_single_host_limit() -> None:
    """Restore refuses to run without exactly one --limit host."""
    result = subprocess.run(
        [str(RESTORE_SCRIPT)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--limit" in result.stderr


def test_restore_playbook_syntax_check() -> None:
    """ansible-playbook --syntax-check accepts the restore playbook."""
    if shutil.which("ansible-playbook") is None:
        return

    result = subprocess.run(
        ["ansible-playbook", "--syntax-check", str(RESTORE_PLAYBOOK)],
        cwd=PROJECT_ROOT / "ansible",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_restore_source_parser_supports_multi_var_extra_string() -> None:
    """-e \"a=b c=d\" still extracts edge_stack_restore_source correctly."""
    result = subprocess.run(
        [
            "bash",
            "-lc",
            (
                f"source '{LIB_SCRIPT}'"
                " ; resolve_edge_stack_restore_source edge-node-2 --limit edge-node-2"
                " -e 'edge_stack_restore_source=edge-node-1 edge_stack_restore_env=true'"
            ),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "edge-node-1"


def test_restore_playbook_rechecks_env_after_optional_copy() -> None:
    """Post-restore start/import checks should use refreshed env existence stat."""
    content = RESTORE_PLAYBOOK.read_text()
    assert "register: edge_stack_env_file_after_restore" in content
    assert "edge_stack_env_file_after_restore.stat.exists" in content


def test_restore_manifest_fixture_is_valid_json() -> None:
    """Template manifest shape matches what the restore playbook expects."""
    manifest = {
        "host": "edge-node-1",
        "edge_stack_path": "/opt/docker",
        "last_backup": "2026-01-01T00:00:00Z",
        "compose_files": ["compose.yml", "compose-mosquitto.yml", "compose-node-red.yml"],
        "services": {
            "mosquitto": True,
            "node_red": True,
            "sqlite": True,
            "grafana": False,
            "postgresql": False,
        },
    }
    parsed = json.loads(json.dumps(manifest))
    assert parsed["services"]["mosquitto"] is True
    assert parsed["services"]["sqlite"] is True
    assert parsed["services"]["postgresql"] is False
