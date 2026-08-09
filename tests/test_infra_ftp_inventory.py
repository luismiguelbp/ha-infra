"""Tests for Ansible inventory host resolution and FTP config loading."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
TEMPLATE_INVENTORY = PROJECT_ROOT / "ansible" / "inventory"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from infra_ftp_test import FtpTestConfigError, load_ftp_config  # noqa: E402
from infra_inventory import InventoryError, list_inventory_hostnames, resolve_inventory_host  # noqa: E402


def test_list_template_inventory_hostnames() -> None:
    names = list_inventory_hostnames(TEMPLATE_INVENTORY)
    assert names == ["edge-node-1", "edge-node-2", "edge-node-3"]


def test_resolve_uses_dns_name_from_host_vars() -> None:
    host = resolve_inventory_host("edge-node-2", inventory_root=TEMPLATE_INVENTORY)
    assert host.name == "edge-node-2"
    assert host.dns_name == "edge-node-2.example.lan"
    assert host.ansible_host == "edge-node-2.example.lan"
    assert host.connect_host == "edge-node-2.example.lan"
    assert host.ftp_enabled is False  # group_vars/all.yml default


def test_resolve_unknown_host() -> None:
    with pytest.raises(InventoryError, match="Unknown inventory host"):
        resolve_inventory_host("missing-host", inventory_root=TEMPLATE_INVENTORY)


def test_load_ftp_config_from_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = tmp_path / "inventory"
    (inventory / "host_vars").mkdir(parents=True)
    (inventory / "hosts.yml").write_text(
        "\n".join(
            [
                "---",
                "all:",
                "  children:",
                "    linux_hosts:",
                "      hosts:",
                "        edge-node-1:",
                "          ansible_host: edge-node-1.example.lan",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (inventory / "host_vars" / "edge-node-1.yml").write_text(
        "\n".join(
            [
                "---",
                "dns_name: edge-node-1.example.lan",
                "ftp_enabled: true",
                "ftp_tls_enabled: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HA_INFRA_FTP_USER", "ftpuser")
    monkeypatch.setenv("HA_INFRA_FTP_PASS", "secret")
    monkeypatch.delenv("HA_INFRA_FTP_TLS_INSECURE", raising=False)

    config = load_ftp_config("edge-node-1", inventory_root=inventory)
    assert config.host == "edge-node-1.example.lan"
    assert config.host_source == "dns_name"
    assert config.tls is True
    assert config.tls_insecure is False
    assert config.user == "ftpuser"


def test_load_ftp_config_tls_follows_host_vars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = tmp_path / "inventory"
    (inventory / "host_vars").mkdir(parents=True)
    (inventory / "hosts.yml").write_text(
        "\n".join(
            [
                "---",
                "all:",
                "  children:",
                "    linux_hosts:",
                "      hosts:",
                "        edge-node-2:",
                "          ansible_host: edge-node-2.example.lan",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (inventory / "host_vars" / "edge-node-2.yml").write_text(
        "\n".join(
            [
                "---",
                "dns_name: edge-node-2.example.lan",
                "ftp_enabled: true",
                "ftp_tls_enabled: false",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HA_INFRA_FTP_USER", "ftpuser")
    monkeypatch.setenv("HA_INFRA_FTP_PASS", "secret")
    monkeypatch.setenv("HA_INFRA_FTP_TLS_INSECURE", "1")

    config = load_ftp_config("edge-node-2", inventory_root=inventory)
    assert config.tls is False
    assert config.tls_insecure is True


def test_load_ftp_config_rejects_disabled_ftp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = tmp_path / "inventory"
    (inventory / "host_vars").mkdir(parents=True)
    (inventory / "hosts.yml").write_text(
        "\n".join(
            [
                "---",
                "all:",
                "  children:",
                "    linux_hosts:",
                "      hosts:",
                "        edge-node-3: {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (inventory / "host_vars" / "edge-node-3.yml").write_text(
        "\n".join(
            [
                "---",
                "dns_name: edge-node-3.example.lan",
                "ftp_enabled: false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HA_INFRA_FTP_USER", "ftpuser")
    monkeypatch.setenv("HA_INFRA_FTP_PASS", "secret")

    with pytest.raises(FtpTestConfigError, match="ftp_enabled is false"):
        load_ftp_config("edge-node-3", inventory_root=inventory)
