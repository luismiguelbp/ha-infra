"""Shared helpers for structural contract tests."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKER_DIR = PROJECT_ROOT / "docker"
ANSIBLE_EDGE_STACK_DEFAULTS = (
    PROJECT_ROOT / "ansible" / "roles" / "edge_stack" / "defaults" / "main.yml"
)
TEMPLATE_HOST_VARS_DIR = PROJECT_ROOT / "ansible" / "inventory" / "host_vars"

# Created manually on each Pi; not shipped from the repository.
MANUAL_EDGE_STACK_DATA_FILES = frozenset({"data/mosquitto/config/passwords_file"})


def parse_ansible_list(key: str) -> list[str]:
    """Return dash-list values under a top-level YAML key in edge_stack defaults."""
    lines = ANSIBLE_EDGE_STACK_DEFAULTS.read_text().splitlines()
    items: list[str] = []
    in_block = False

    for line in lines:
        if line.startswith(f"{key}:"):
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        value = stripped[2:].strip()
        if value.startswith("src:"):
            value = value.split(":", 1)[1].strip()
        items.append(value)

    return items


def parse_ansible_scalar(key: str) -> str:
    """Return a top-level scalar value from edge_stack defaults."""
    for line in ANSIBLE_EDGE_STACK_DEFAULTS.read_text().splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    raise KeyError(key)


def parse_host_var_list(host_vars_file: Path, key: str) -> list[str] | None:
    """Return a dash-list value from a host_vars YAML file, or None when unset."""
    lines = host_vars_file.read_text().splitlines()
    items: list[str] = []
    in_block = False

    for line in lines:
        if line.startswith(f"{key}:"):
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        items.append(stripped[2:].strip())

    return items or None


def parse_env_example_var(key: str) -> str:
    """Return a variable value from docker/env.example."""
    env_example = DOCKER_DIR / "env.example"
    for line in env_example.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    raise KeyError(key)


def read_compose_images(path: Path) -> dict[str, str]:
    """Map service name to image tag from a compose file."""
    images: dict[str, str] = {}
    current_service: str | None = None

    for line in path.read_text().splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current_service = line.strip()[:-1]
            continue
        if current_service and line.strip().startswith("image:"):
            images[current_service] = line.split(":", 1)[1].strip()

    return images


def read_compose_host_ports(path: Path, service: str) -> list[int]:
    """Return host-side TCP ports published by a compose service."""
    ports: list[int] = []
    current_service: str | None = None
    in_ports = False

    for line in path.read_text().splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            current_service = line.strip()[:-1]
            in_ports = False
            continue
        if current_service != service:
            continue
        stripped = line.strip()
        if stripped == "ports:":
            in_ports = True
            continue
        if not in_ports:
            continue
        if stripped.startswith("- "):
            mapping = stripped.removeprefix("- ").strip('"')
            host_port = mapping.split(":")[0]
            if host_port.isdigit():
                ports.append(int(host_port))
            continue
        if stripped and not stripped.startswith("- "):
            in_ports = False

    return ports


def read_mosquitto_listeners(path: Path) -> list[tuple[int, str | None]]:
    """Return active (port, protocol) pairs from mosquitto.conf listener lines."""
    listeners: list[tuple[int, str | None]] = []
    pending_port: int | None = None
    pending_protocol: str | None = None

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("listener "):
            parts = line.split()
            pending_port = int(parts[1])
            pending_protocol = None
            continue
        if pending_port is not None and line.startswith("protocol "):
            pending_protocol = line.split(maxsplit=1)[1]
            listeners.append((pending_port, pending_protocol))
            pending_port = None
            pending_protocol = None
            continue
        if pending_port is not None and not line.startswith("socket_domain"):
            listeners.append((pending_port, pending_protocol))
            pending_port = None
            pending_protocol = None

    return listeners


def read_mosquitto_setting(path: Path, key: str) -> str | None:
    """Return the first active value for a mosquitto.conf setting."""
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{key} "):
            return line.split(maxsplit=1)[1]
    return None
