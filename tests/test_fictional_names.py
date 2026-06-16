"""Ensure committed template files use only fictional DNS names."""

import re
from pathlib import Path

from contract_helpers import PROJECT_ROOT

# Only *.example.lan is allowed in this repository.
LAN_PATTERN = re.compile(r"\b[a-z0-9][a-z0-9.-]*\.lan\b", re.IGNORECASE)

SCAN_SUFFIXES = {".md", ".mdc", ".py", ".yml", ".yaml", ".sh", ".js", ".j2"}
SCAN_SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def _scan_paths() -> list[Path]:
    paths: list[Path] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SCAN_SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in SCAN_SUFFIXES:
            continue
        paths.append(path)
    return paths


def _is_allowed_lan(hostname: str) -> bool:
    name = hostname.lower()
    return name == "example.lan" or name.endswith(".example.lan")


def test_committed_files_use_fictional_lan_domains_only() -> None:
    """LAN hostnames in repo files must use the example.lan template domain."""
    violations: list[str] = []

    for path in _scan_paths():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in LAN_PATTERN.finditer(line):
                hostname = match.group(0)
                if _is_allowed_lan(hostname):
                    continue
                rel_path = path.relative_to(PROJECT_ROOT)
                violations.append(f"{rel_path}:{line_no}: {hostname.lower()}")

    assert not violations, "Non-fictional LAN names found:\n" + "\n".join(violations)
