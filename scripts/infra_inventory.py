#!/usr/bin/env python3
"""Resolve Ansible inventory host facts for ha-infra client helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ENV_CONFIG = "HA_INFRA_CONFIG"


class InventoryError(Exception):
    """Inventory path or host resolution failed."""


@dataclass(frozen=True)
class InventoryHost:
    """Merged facts for one inventory hostname."""

    name: str
    dns_name: str | None
    ansible_host: str | None
    ftp_enabled: bool | None
    ftp_tls_enabled: bool | None

    @property
    def connect_host(self) -> str:
        """Preferred client hostname: dns_name, then ansible_host, then inventory name."""

        for value in (self.dns_name, self.ansible_host, self.name):
            if value:
                return value
        return self.name


def inventory_root_from_env() -> Path:
    """Return `$HA_INFRA_CONFIG/ansible/inventory`."""

    config = (os.environ.get(ENV_CONFIG) or "").strip()
    if not config:
        raise InventoryError(f"{ENV_CONFIG} is not set")
    root = Path(config).expanduser() / "ansible" / "inventory"
    if not root.is_dir():
        raise InventoryError(f"Inventory directory not found: {root}")
    return root


def list_inventory_hostnames(inventory_root: Path) -> list[str]:
    """Return inventory hostnames from hosts.yml (order preserved)."""

    hosts_file = inventory_root / "hosts.yml"
    if not hosts_file.is_file():
        raise InventoryError(f"Missing inventory file: {hosts_file}")
    data = _load_yaml(hosts_file)
    names: list[str] = []
    _collect_hostnames(_inventory_root_node(data), names)
    if not names:
        raise InventoryError(f"No hosts found in {hosts_file}")
    return names


def resolve_inventory_host(limit: str, inventory_root: Path | None = None) -> InventoryHost:
    """Resolve one inventory hostname from hosts.yml + host_vars (+ group defaults)."""

    host = limit.strip()
    if not host:
        raise InventoryError("--limit hostname must not be empty")
    if "*" in host or ":" in host or "," in host:
        raise InventoryError("--limit must be a single inventory hostname, not a pattern")

    root = inventory_root or inventory_root_from_env()
    hosts_file = root / "hosts.yml"
    if not hosts_file.is_file():
        raise InventoryError(f"Missing inventory file: {hosts_file}")

    hosts_data = _load_yaml(hosts_file)
    inventory_node = _inventory_root_node(hosts_data)
    inline = _find_host_inline_vars(inventory_node, host)
    if inline is None:
        known = ", ".join(list_inventory_hostnames(root))
        raise InventoryError(f"Unknown inventory host {host!r}. Known hosts: {known}")

    groups = _groups_for_host(inventory_node, host)
    merged: dict[str, Any] = {}
    all_vars = root / "group_vars" / "all.yml"
    if all_vars.is_file():
        merged.update(_load_yaml(all_vars) or {})
    for group in groups:
        group_file = root / "group_vars" / f"{group}.yml"
        if group_file.is_file():
            merged.update(_load_yaml(group_file) or {})

    if isinstance(inline, dict):
        merged.update(inline)

    host_vars_file = root / "host_vars" / f"{host}.yml"
    if host_vars_file.is_file():
        merged.update(_load_yaml(host_vars_file) or {})

    return InventoryHost(
        name=host,
        dns_name=_optional_str(merged.get("dns_name")),
        ansible_host=_optional_str(merged.get("ansible_host")),
        ftp_enabled=_optional_bool(merged.get("ftp_enabled")),
        ftp_tls_enabled=_optional_bool(merged.get("ftp_tls_enabled")),
    )


def _inventory_root_node(data: Any) -> Any:
    """Return the Ansible inventory root node (prefer the `all` group)."""

    if isinstance(data, dict) and "all" in data:
        return data["all"]
    return data


def _load_yaml(path: Path) -> Any:
    try:
        data = yaml.safe_load(path.read_text())
    except OSError as exc:
        raise InventoryError(f"Cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise InventoryError(f"Invalid YAML in {path}: {exc}") from exc
    return data if data is not None else {}


def _collect_hostnames(node: Any, names: list[str]) -> None:
    if not isinstance(node, dict):
        return
    hosts = node.get("hosts")
    if isinstance(hosts, dict):
        for name in hosts:
            if isinstance(name, str) and name not in names:
                names.append(name)
    children = node.get("children")
    if isinstance(children, dict):
        for child in children.values():
            _collect_hostnames(child, names)


def _find_host_inline_vars(node: Any, host: str) -> dict[str, Any] | None:
    """Return inline host vars dict (possibly empty) when host exists, else None."""

    if not isinstance(node, dict):
        return None
    hosts = node.get("hosts")
    if isinstance(hosts, dict) and host in hosts:
        value = hosts[host]
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return {}
    children = node.get("children")
    if isinstance(children, dict):
        for child in children.values():
            found = _find_host_inline_vars(child, host)
            if found is not None:
                return found
    return None


def _groups_for_host(node: Any, host: str, path: list[str] | None = None) -> list[str]:
    """Return group names under the inventory root that contain the host."""

    path = path or []
    if not isinstance(node, dict):
        return []
    found: list[str] = []
    hosts = node.get("hosts")
    if isinstance(hosts, dict) and host in hosts:
        found.extend(path)
    children = node.get("children")
    if isinstance(children, dict):
        for name, child in children.items():
            if not isinstance(name, str):
                continue
            found.extend(_groups_for_host(child, host, path + [name]))
    return found


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return None
