"""Structural tests for repository layout and Ansible/Docker alignment."""

import yaml

from contract_helpers import (
    DOCKER_DIR,
    MANUAL_EDGE_STACK_DATA_FILES,
    PROJECT_ROOT,
    parse_ansible_list,
    parse_env_example_var,
)


def test_edge_stack_compose_files_exist() -> None:
    """Every compose file referenced by Ansible exists under docker/."""
    for compose_file in parse_ansible_list("edge_stack_compose_files"):
        assert (DOCKER_DIR / compose_file).is_file(), compose_file


def test_compose_file_list_matches_env_example() -> None:
    """docker/env.example COMPOSE_FILE is a subset of deployed compose files."""
    ansible_files = parse_ansible_list("edge_stack_compose_files")
    env_files = parse_env_example_var("COMPOSE_FILE").split(",")
    assert all(file in ansible_files for file in env_files)


def test_edge_stack_data_files_exist_in_repo() -> None:
    """Shipped edge stack data files exist under docker/ (manual files excluded)."""
    for data_file in parse_ansible_list("edge_stack_data_files"):
        if data_file in MANUAL_EDGE_STACK_DATA_FILES:
            continue
        assert (DOCKER_DIR / data_file).is_file(), data_file


def test_manual_edge_stack_data_files_are_gitignored() -> None:
    """Files created on each Pi are excluded from version control."""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()
    for data_file in MANUAL_EDGE_STACK_DATA_FILES:
        assert f"docker/{data_file}" in gitignore, data_file


def test_infra_docker_status_script_and_playbook_exist() -> None:
    """Docker status wrapper and playbook are present for fleet checks."""
    script = PROJECT_ROOT / "bin" / "infra-docker-status"
    playbook = PROJECT_ROOT / "ansible" / "playbooks" / "docker-status.yml"

    assert script.is_file()
    assert script.stat().st_mode & 0o111
    assert playbook.is_file()


def test_infra_backup_script_and_playbook_exist() -> None:
    """Backup wrapper and playbook are present for host mirrors."""
    script = PROJECT_ROOT / "bin" / "infra-backup-edge-stack"
    playbook = PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-backup.yml"

    assert script.is_file()
    assert script.stat().st_mode & 0o111
    assert playbook.is_file()


def test_infra_restore_script_and_playbook_exist() -> None:
    """Restore wrapper and playbook are present for manual disaster recovery."""
    script = PROJECT_ROOT / "bin" / "infra-restore-edge-stack"
    playbook = PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-restore.yml"

    assert script.is_file()
    assert script.stat().st_mode & 0o111
    assert playbook.is_file()


def test_infra_configure_samba_script_and_role_files_exist() -> None:
    """Samba wrapper and role files are present for public SMB share setup."""
    script = PROJECT_ROOT / "bin" / "infra-configure-samba"
    defaults_file = PROJECT_ROOT / "ansible" / "roles" / "samba" / "defaults" / "main.yml"
    tasks_file = PROJECT_ROOT / "ansible" / "roles" / "samba" / "tasks" / "main.yml"
    template_file = PROJECT_ROOT / "ansible" / "roles" / "samba" / "templates" / "smb.conf.j2"
    handlers_file = PROJECT_ROOT / "ansible" / "roles" / "samba" / "handlers" / "main.yml"

    assert script.is_file()
    assert script.stat().st_mode & 0o111
    assert defaults_file.is_file()
    assert tasks_file.is_file()
    assert template_file.is_file()
    assert handlers_file.is_file()


def test_env_example_includes_config_and_backup_vars() -> None:
    """.env.example documents external config and backup paths."""
    env_example = (PROJECT_ROOT / ".env.example").read_text()
    assert "HA_INFRA_CONFIG=" in env_example
    assert "HA_INFRA_BACKUP=" in env_example


def test_edge_stack_utility_playbooks_preserve_inventory_precedence() -> None:
    """Utility playbooks must not load role defaults as play vars."""
    playbooks = [
        PROJECT_ROOT / "ansible" / "playbooks" / "docker-status.yml",
        PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-backup.yml",
        PROJECT_ROOT / "ansible" / "playbooks" / "edge-stack-restore.yml",
    ]

    for playbook in playbooks:
        play = yaml.safe_load(playbook.read_text())[0]
        assert "vars_files" not in play, playbook.name

        pre_tasks = play.get("pre_tasks", [])
        assert any(
            task.get("ansible.builtin.include_vars", {}).get("name")
            == "edge_stack_role_defaults"
            for task in pre_tasks
        ), playbook.name
