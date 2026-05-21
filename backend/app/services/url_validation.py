"""Validation helpers for URLs that the backend will call server-side."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from ..config import settings


_LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}


class ServiceUrlError(ValueError):
    """Raised when a user-configured upstream URL is unsafe or invalid."""


def _is_blocked_address(host: str, *, allow_private: bool) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return True
    if ip.is_loopback and not allow_private:
        return True
    if not allow_private and (ip.is_private or ip.is_reserved):
        return True
    return False


def validate_service_url(value: str, *, field_name: str = "URL") -> str:
    """Validate a user-controlled URL before the server issues requests to it."""
    url = (value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ServiceUrlError(f"{field_name} must be an http(s) URL")
    if parsed.username or parsed.password:
        raise ServiceUrlError(f"{field_name} must not include credentials")

    host = parsed.hostname
    if not host:
        raise ServiceUrlError(f"{field_name} must include a host")

    allow_private = settings.ALLOW_PRIVATE_SERVICE_URLS
    host_lower = host.lower().rstrip(".")
    if host_lower in _LOCAL_HOSTNAMES and not allow_private:
        raise ServiceUrlError(
            f"{field_name} points to a local address; set ALLOW_PRIVATE_SERVICE_URLS=true to allow it"
        )
    if _is_blocked_address(host_lower, allow_private=allow_private):
        raise ServiceUrlError(
            f"{field_name} points to a restricted network address"
        )

    try:
        infos = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return url.rstrip("/")

    for info in infos:
        address = info[4][0]
        if _is_blocked_address(address, allow_private=allow_private):
            raise ServiceUrlError(
                f"{field_name} resolves to a restricted network address"
            )
    return url.rstrip("/")
