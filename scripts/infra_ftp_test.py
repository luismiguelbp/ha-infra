#!/usr/bin/env python3
"""FTP/FTPS connectivity and read/write probes for ha-infra fleet hosts."""

from __future__ import annotations

import argparse
import io
import os
import ssl
import sys
import time
from ftplib import FTP, FTP_TLS, error_perm, error_proto, error_reply, error_temp


ENV_HOST = "HA_INFRA_FTP_HOST"
ENV_USER = "HA_INFRA_FTP_USER"
ENV_PASSWORD = "HA_INFRA_FTP_PASSWORD"
ENV_PORT = "HA_INFRA_FTP_PORT"
ENV_TLS = "HA_INFRA_FTP_TLS"
ENV_TLS_INSECURE = "HA_INFRA_FTP_TLS_INSECURE"
DEFAULT_PORT = 21
PROBE_PREFIX = ".ha-infra-ftp-probe-"


class FtpTestConfigError(Exception):
    """Missing or invalid FTP test configuration."""


class FtpTestError(Exception):
    """FTP operation failed."""


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


def load_ftp_config() -> tuple[str, str, str, int, bool, bool]:
    host = _required_env(ENV_HOST)
    user = _required_env(ENV_USER)
    password = _required_env(ENV_PASSWORD)
    port = _ftp_port()
    tls = _env_flag(ENV_TLS)
    tls_insecure = _env_flag(ENV_TLS_INSECURE)
    return host, user, password, port, tls, tls_insecure


def connect_ftp() -> FTP:
    host, user, password, port, tls, tls_insecure = load_ftp_config()
    if tls:
        context = ssl.create_default_context()
        if tls_insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        ftp: FTP = FTP_TLS(context=context)
        ftp.connect(host=host, port=port, timeout=30)
        ftp.login(user=user, passwd=password)
        ftp.prot_p()
        return ftp

    ftp = FTP()
    ftp.connect(host=host, port=port, timeout=30)
    ftp.login(user=user, passwd=password)
    return ftp


def cmd_status(_args: argparse.Namespace) -> int:
    try:
        ftp = connect_ftp()
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

    host, user, _, port, tls, tls_insecure = load_ftp_config()
    print("FTP status OK")
    print(f"  host: {host}")
    print(f"  port: {port}")
    print(f"  user: {user}")
    print(f"  tls: {'yes' if tls else 'no'}")
    if tls:
        print(f"  tls_insecure: {'yes' if tls_insecure else 'no'}")
    print(f"  pwd: {pwd}")
    print(f"  entries: {len(names)}")
    return 0


def probe_name() -> str:
    return f"{PROBE_PREFIX}{int(time.time())}.txt"


def cmd_write(args: argparse.Namespace) -> int:
    remote_name = args.remote or probe_name()
    payload = args.payload or f"ha-infra ftp probe {time.time()}\n"

    try:
        ftp = connect_ftp()
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

    host, _, _, port, tls, _ = load_ftp_config()
    print("FTP write OK")
    print(f"  host: {host}")
    print(f"  port: {port}")
    print(f"  tls: {'yes' if tls else 'no'}")
    print(f"  remote: {remote_name}")
    print(f"  kept: {'yes' if args.keep else 'no'}")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    if not args.remote:
        print("FTP read requires --remote PATH", file=sys.stderr)
        return 1

    try:
        ftp = connect_ftp()
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
    host, _, _, port, tls, _ = load_ftp_config()
    print("FTP read OK")
    print(f"  host: {host}")
    print(f"  port: {port}")
    print(f"  tls: {'yes' if tls else 'no'}")
    print(f"  remote: {args.remote}")
    print(f"  bytes: {len(data)}")
    if args.show_content:
        print(data.decode("utf-8", errors="replace"), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infra-ftp-test",
        description=(
            "Test FTP/FTPS connectivity against a fleet host using "
            f"{ENV_HOST}, {ENV_USER}, and {ENV_PASSWORD} from the OS environment. "
            f"Set {ENV_TLS}=1 for explicit FTPS; {ENV_TLS_INSECURE}=1 for self-signed certs."
        ),
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
