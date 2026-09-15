"""SSRF protection, URL building, API key auth."""

import ipaddress
import logging
import socket
from typing import List, Optional
from urllib.parse import quote

from fastapi import Header, HTTPException

from .config import get_config

logger = logging.getLogger("camera_server.security")


# ============================================================
# Domain exceptions
# ============================================================


class SecurityError(Exception):
    """Raised when a request violates security policy."""


# ============================================================
# URL building
# ============================================================


def build_rtsp_url(
    host: str,
    port: int,
    protocol: str,
    username: str,
    password: str,
    path: str,
) -> str:
    """Build RTSP URL with properly encoded credentials."""
    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    if user and pwd:
        auth = f"{user}:{pwd}@"
    elif user:
        auth = f"{user}@"
    else:
        auth = ""
    p = path or ""
    if p and not p.startswith("/"):
        p = "/" + p
    return f"{protocol.lower()}://{auth}{host}:{port}{p}"


# ============================================================
# SSRF protection
# ============================================================


def _resolve_host(host: str) -> List[str]:
    """Return all IPs for a hostname."""
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
        return list({info[4][0] for info in infos})
    except socket.gaierror as e:
        raise SecurityError(f"Cannot resolve host '{host}': {e}")


def validate_host_against_networks(
    host: str,
    allowed_networks: List[str],
) -> None:
    """Raise SecurityError if host is outside allowed networks."""
    if not allowed_networks:
        raise SecurityError("No allowed networks configured")

    networks = [ipaddress.ip_network(n, strict=False) for n in allowed_networks]
    for ip_str in _resolve_host(host):
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SecurityError(f"Invalid resolved IP: {ip_str}")
        if not any(ip in net for net in networks):
            raise SecurityError(f"Host '{host}' ({ip_str}) is outside allowed networks")


# ============================================================
# API key dependency (FastAPI)
# ============================================================


async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    cfg = get_config()
    if not cfg.server.api_key:
        return  # disabled
    if x_api_key != cfg.server.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
