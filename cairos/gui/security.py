"""Security helpers for the local-only CAIROS GUI."""

from __future__ import annotations

import os
import re
import secrets


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"[A-Za-z0-9_-]{32,}"),
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
    return host in {"127.0.0.1", "localhost", "::1"}

