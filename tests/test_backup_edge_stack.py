"""Structural and syntax checks for edge stack backup."""

import shutil
import subprocess
from pathlib import Path

import yaml

from contract_helpers import PROJECT_ROOT

BACKUP_SCRIPT = PROJECT_ROOT / "bin" / "infra-backup-edge-stack"
BACKUP_PLAYBOOK = PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-backup.yml"

REQUIRED_PLAYBOOK_VARS = {
    "edge_stack_backup_stop_grafana",
    "edge_stack_backup_stop_node_red",
}

REQUIRED_TASK_NAMES = {
    "Backup Node-RED and SQLite data with optional stop",
    "Mirror SQLite data directory",
    "Start Node-RED after backup",
    "Write host backup manifest",
}


def _playbook_task_names(playbook: dict) -> set[str]:
    names: set[str] = set()
    for play in playbook:
        for task in play.get("tasks", []):
            if "name" in task:
                names.add(task["name"])
            for block_task in task.get("block", []):
                if "name" in block_task:
                    names.add(block_task["name"])
            for always_task in task.get("always", []):
                if "name" in always_task:
                    names.add(always_task["name"])
    return names


def test_infra_backup_script_and_playbook_exist() -> None:
    """Backup wrapper and playbook are present."""
    assert BACKUP_SCRIPT.is_file()
    assert BACKUP_SCRIPT.stat().st_mode & 0o111
    assert BACKUP_PLAYBOOK.is_file()


def test_backup_playbook_declares_required_vars() -> None:
    """Backup playbook exposes operator-facing stop flags."""
    playbook = yaml.safe_load(BACKUP_PLAYBOOK.read_text())
    play_vars = playbook[0]["vars"]
    assert REQUIRED_PLAYBOOK_VARS.issubset(play_vars.keys())
    assert play_vars["edge_stack_backup_stop_node_red"] is True


def test_backup_playbook_includes_sqlite_tasks() -> None:
    """Backup playbook mirrors SQLite with Node-RED stop/restart safety."""
    playbook = yaml.safe_load(BACKUP_PLAYBOOK.read_text())
    task_names = _playbook_task_names(playbook)
    missing = REQUIRED_TASK_NAMES - task_names
    assert not missing, f"Missing tasks: {sorted(missing)}"


def test_backup_manifest_includes_sqlite_service_flag() -> None:
    """Manifest documents sqlite alongside other edge stack services."""
    content = BACKUP_PLAYBOOK.read_text()
    assert '"sqlite":' in content


def test_backup_playbook_syntax_check() -> None:
    """ansible-playbook --syntax-check accepts the backup playbook."""
    if shutil.which("ansible-playbook") is None:
        return

    result = subprocess.run(
        ["ansible-playbook", "--syntax-check", str(BACKUP_PLAYBOOK)],
        cwd=PROJECT_ROOT / "ansible",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
