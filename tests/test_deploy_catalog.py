"""Structural tests for catalog deploy playbook and script."""

import shutil
import subprocess
from pathlib import Path

import yaml

from contract_helpers import PROJECT_ROOT

DEPLOY_SCRIPT = PROJECT_ROOT / "bin" / "infra-deploy-catalog"
DEPLOY_PLAYBOOK = PROJECT_ROOT / "ansible" / "playbooks" / "deploy-catalog.yml"
COMPOSE_NODE_RED = PROJECT_ROOT / "docker" / "compose-node-red.yml"


def test_infra_deploy_catalog_script_and_playbook_exist() -> None:
    assert DEPLOY_SCRIPT.is_file()
    assert DEPLOY_SCRIPT.stat().st_mode & 0o111
    assert DEPLOY_PLAYBOOK.is_file()


def test_compose_node_red_mounts_catalog_directory() -> None:
    content = COMPOSE_NODE_RED.read_text()
    assert "data/catalog:/data/catalog:ro" in content


def test_deploy_catalog_playbook_restarts_node_red() -> None:
    content = DEPLOY_PLAYBOOK.read_text()
    assert "catalog_src" in content
    assert "docker compose restart node-red" in content
    assert "remote_catalog_file" in content


def test_deploy_catalog_playbook_syntax_check() -> None:
    if shutil.which("ansible-playbook") is None:
        return

    result = subprocess.run(
        ["ansible-playbook", "--syntax-check", str(DEPLOY_PLAYBOOK)],
        cwd=PROJECT_ROOT / "ansible",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_backup_playbook_includes_catalog_mirror() -> None:
    content = (PROJECT_ROOT / "ansible/playbooks/edge-stack-backup.yml").read_text()
    assert "Mirror catalog data directory" in content
    assert '"catalog":' in content


def test_restore_playbook_includes_catalog_restore() -> None:
    content = (PROJECT_ROOT / "ansible/playbooks/edge-stack-restore.yml").read_text()
    assert "Restore catalog data directory" in content
