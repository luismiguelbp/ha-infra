#!/usr/bin/env python3
"""FTP/FTPS connectivity and read/write probes for ha-infra fleet hosts."""

from __future__ import annotations

import argparse
import io
import os
import ssl
import sys
import time
from dataclasses import dataclass
from ftplib import FTP, FTP_TLS, error_perm, error_proto, error_reply, error_temp
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from infra_inventory import InventoryError, InventoryHost, resolve_inventory_host

ENV_USER = "HA_INFRA_FTP_USER"
ENV_PASSWORD = "HA_INFRA_FTP_PASS"
ENV_PORT = "HA_INFRA_FTP_PORT"
ENV_TLS_INSECURE = "HA_INFRA_FTP_TLS_INSECURE"
DEFAULT_PORT = 21
PROBE_PREFIX = ".ha-infra-ftp-probe-"


class FtpTestConfigError(Exception):
    """Missing or invalid FTP test configuration."""


@dataclass(frozen=True)
class FtpTestConfig:
    """Resolved FTP client settings (never log password)."""

    host: str
    user: str
    password: str
    port: int
    tls: bool
    tls_insecure: bool
    inventory_host: str
    host_source: str


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise FtpTestConfigError(f"{name} is not set")
    return value


def _env_flag(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _ftp_port() -> int:
    raw = os.environ.get(ENV_PORT, "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError as exc:
        raise FtpTestConfigError(f"{ENV_PORT} must be an integer") from exc
    if port < 1 or port > 65535:
        raise FtpTestConfigError(f"{ENV_PORT} must be between 1 and 65535")
    return port


def _host_source(inv: InventoryHost) -> str:
    if inv.dns_name:
        return "dns_name"
    if inv.ansible_host:
        return "ansible_host"
    return "inventory_hostname"


def load_ftp_config(limit: str, inventory_root: Path | None = None) -> FtpTestConfig:
    try:
        inv = resolve_inventory_host(limit, inventory_root=inventory_root)
    except InventoryError as exc:
        raise FtpTestConfigError(str(exc)) from exc

    if inv.ftp_enabled is False:
        raise FtpTestConfigError(
            f"ftp_enabled is false for inventory host {inv.name!r}; "
            "enable FTP in host_vars or choose another --limit host"
        )

    return FtpTestConfig(
        host=inv.connect_host,
        user=_required_env(ENV_USER),
        password=_required_env(ENV_PASSWORD),
        port=_ftp_port(),
        tls=bool(inv.ftp_tls_enabled),
        tls_insecure=_env_flag(ENV_TLS_INSECURE),
        inventory_host=inv.name,
        host_source=_host_source(inv),
    )


def connect_ftp(config: FtpTestConfig) -> FTP:
    if config.tls:
        context = ssl.create_default_context()
        if config.tls_insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        ftp: FTP = FTP_TLS(context=context)
        ftp.connect(host=config.host, port=config.port, timeout=30)
        ftp.login(user=config.user, passwd=config.password)
        ftp.prot_p()
        return ftp

    ftp = FTP()
    ftp.connect(host=config.host, port=config.port, timeout=30)
    ftp.login(user=config.user, passwd=config.password)
    return ftp


def _load_config(args: argparse.Namespace) -> FtpTestConfig:
    inventory_root = Path(args.inventory) if getattr(args, "inventory", None) else None
    return load_ftp_config(args.limit, inventory_root=inventory_root)


def cmd_status(args: argparse.Namespace) -> int:
    try:
        config = _load_config(args)
        ftp = connect_ftp(config)
    except FtpTestConfigError as exc:
        print(f"FTP test configuration error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ssl.SSLError, error_perm, error_proto, error_reply, error_temp) as exc:
        print(f"FTP status check failed: {exc}", file=sys.stderr)
        return 2

    try:
        pwd = ftp.pwd()
        names = ftp.nlst()
    finally:
        ftp.quit()

    print("FTP status OK")
    print(f"  inventory: {config.inventory_host}")
    print(f"  host: {config.host} ({config.host_source})")
    print(f"  port: {config.port}")
    print(f"  user: {config.user}")
    print(f"  tls: {'yes' if config.tls else 'no'}")
    if config.tls:
        print(f"  tls_insecure: {'yes' if config.tls_insecure else 'no'}")
    print(f"  pwd: {pwd}")
    print(f"  entries: {len(names)}")
    return 0


def probe_name() -> str:
    return f"{PROBE_PREFIX}{int(time.time())}.txt"


def cmd_write(args: argparse.Namespace) -> int:
    remote_name = args.remote or probe_name()
    payload = args.payload or f"ha-infra ftp probe {time.time()}\n"

    try:
        config = _load_config(args)
        ftp = connect_ftp(config)
    except FtpTestConfigError as exc:
        print(f"FTP test configuration error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ssl.SSLError, error_perm, error_proto, error_reply, error_temp) as exc:
        print(f"FTP write check failed: {exc}", file=sys.stderr)
        return 2

    try:
        ftp.storbinary(f"STOR {remote_name}", io.BytesIO(payload.encode("utf-8")))
        if not args.keep:
            ftp.delete(remote_name)
    except (OSError, ssl.SSLError, error_perm, error_proto, error_reply, error_temp) as exc:
        print(f"FTP write check failed: {exc}", file=sys.stderr)
        return 2
    finally:
        ftp.quit()

    print("FTP write OK")
    print(f"  inventory: {config.inventory_host}")
    print(f"  host: {config.host} ({config.host_source})")
    print(f"  port: {config.port}")
    print(f"  tls: {'yes' if config.tls else 'no'}")
    print(f"  remote: {remote_name}")
    print(f"  kept: {'yes' if args.keep else 'no'}")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    if not args.remote:
        print("FTP read requires --remote PATH", file=sys.stderr)
        return 1

    try:
        config = _load_config(args)
        ftp = connect_ftp(config)
    except FtpTestConfigError as exc:
        print(f"FTP test configuration error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ssl.SSLError, error_perm, error_proto, error_reply, error_temp) as exc:
        print(f"FTP read check failed: {exc}", file=sys.stderr)
        return 2

    buffer = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {args.remote}", buffer.write)
    except (OSError, ssl.SSLError, error_perm, error_proto, error_reply, error_temp) as exc:
        print(f"FTP read check failed: {exc}", file=sys.stderr)
        return 2
    finally:
        ftp.quit()

    data = buffer.getvalue()
    print("FTP read OK")
    print(f"  inventory: {config.inventory_host}")
    print(f"  host: {config.host} ({config.host_source})")
    print(f"  port: {config.port}")
    print(f"  tls: {'yes' if config.tls else 'no'}")
    print(f"  remote: {args.remote}")
    print(f"  bytes: {len(data)}")
    if args.show_content:
        print(data.decode("utf-8", errors="replace"), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infra-ftp-test",
        description=(
            "Test FTP/FTPS against one inventory host. "
            "Hostname comes from host_vars dns_name (fallback ansible_host). "
            f"TLS follows inventory ftp_tls_enabled. "
            f"Credentials: {ENV_USER} / {ENV_PASSWORD} in the OS environment. "
            f"Self-signed certs: {ENV_TLS_INSECURE}=1."
        ),
    )
    parser.add_argument(
        "--limit",
        "-l",
        required=True,
        metavar="HOST",
        help="Inventory hostname (exactly one), e.g. edge-node-1.",
    )
    parser.add_argument(
        "--inventory",
        help=argparse.SUPPRESS,
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    status_parser = subparsers.add_parser("status", help="Connect, login, and list the share.")
    status_parser.set_defaults(func=cmd_status)

    write_parser = subparsers.add_parser("write", help="Upload a probe file (deleted unless --keep).")
    write_parser.add_argument(
        "--remote",
        help=f"Remote filename (default: {PROBE_PREFIX}<timestamp>.txt).",
    )
    write_parser.add_argument(
        "--payload",
        help="Optional probe file contents.",
    )
    write_parser.add_argument(
        "--keep",
        action="store_true",
        help="Leave the probe file on the server after upload.",
    )
    write_parser.set_defaults(func=cmd_write)

    read_parser = subparsers.add_parser("read", help="Download a remote file.")
    read_parser.add_argument(
        "--remote",
        required=True,
        help="Remote file path to download.",
    )
    read_parser.add_argument(
        "--show-content",
        action="store_true",
        help="Print downloaded file contents to stdout.",
    )
    read_parser.set_defaults(func=cmd_read)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
