"""Security helpers for the local-only CAIROS GUI."""

from __future__ import annotations

import os
import re
import secrets
from urllib.parse import urlparse


SECRET_PATTERNS = [
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"hf_[A-Za-z0-9_]{20,}"),
]


def generate_session_token() -> str:
    """Return a per-launch token used for local state-changing requests."""
    return secrets.token_urlsafe(32)


def token_matches(expected: str, supplied: str | None) -> bool:
    """Constant-time token comparison."""
    return bool(supplied) and secrets.compare_digest(expected, supplied)


def mask_secret_text(value: str) -> str:
    """Redact common token-looking strings from display/log text."""
    masked = value
    for env_value in os.environ.values():
        if env_value and len(env_value) >= 12:
            masked = masked.replace(env_value, "<redacted>")
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub("<redacted>", masked)
    return masked


def is_local_host(host: str) -> bool:
    """Return true only for localhost bind targets."""
    return host in {"127.0.0.1", "localhost"}


def same_origin(request_url: object, origin: str | None) -> bool:
    """Return true when Origin is absent or exactly matches request origin."""
    if not origin:
        return True
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.hostname:
        return False
    request_scheme = str(getattr(request_url, "scheme", ""))
    request_host = str(getattr(request_url, "hostname", "") or "")
    request_port = getattr(request_url, "port", None)
    origin_port = parsed.port
    if parsed.scheme != request_scheme or parsed.hostname != request_host:
        return False
    default_port = 443 if request_scheme == "https" else 80
    return (origin_port or default_port) == (request_port or default_port)
