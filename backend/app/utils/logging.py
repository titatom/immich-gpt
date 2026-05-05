from urllib.parse import urlsplit, urlunsplit


def redact_url(url: str | None) -> str:
    """Return a URL safe for logs by removing any embedded credentials."""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "[redacted]"
    if not parts.netloc:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
