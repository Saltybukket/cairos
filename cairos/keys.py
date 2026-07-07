"""Helpers for API key environment variable setup.

CAIROS stores environment variable names in config, not raw API key values.
Raw values may be read from ``os.environ`` only for explicit reveal/setup flows.
"""

from __future__ import annotations

import os
import re

from .config import detect_shell_kind

ENV_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RAW_KEY_PREFIXES = ("sk-", "sk-or-v1-", "AIza", "gsk_", "hf_", "pypi-")
TOKENISH_RE = re.compile(r"^[A-Za-z0-9_-]{40,}$")


def looks_like_raw_key(value: str) -> bool:
    text = value.strip()
    return bool(text) and (text.startswith(RAW_KEY_PREFIXES) or bool(TOKENISH_RE.fullmatch(text)))


def validate_env_var_name(name: str) -> tuple[bool, str]:
    text = name.strip()
    if not text:
        return False, "Environment variable name is required."
    if looks_like_raw_key(text):
        return False, (
            "This looks like an API key value, not an environment variable name. "
            "Use a name such as OPENROUTER_API_KEY here, then set the key value in the key setup section."
        )
    if not ENV_VAR_RE.fullmatch(text):
        return False, "Environment variable names must match ^[A-Za-z_][A-Za-z0-9_]*$."
    return True, ""


def require_valid_env_var_name(name: str) -> str:
    text = name.strip()
    ok, message = validate_env_var_name(text)
    if not ok:
        raise ValueError(message)
    return text


def key_status(name: str, environ: dict[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return "available" if env.get(name) else "missing"


def _quote_posix(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`") + '"'


def _quote_powershell(value: str) -> str:
    return '"' + value.replace("`", "``").replace('"', '`"').replace("$", "`$") + '"'


def _quote_cmd(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def normalize_shell(shell: str | None = None) -> str:
    guessed = (shell or "auto").lower()
    if guessed in {"auto", ""}:
        guessed = detect_shell_kind()
    if guessed in {"bash", "zsh", "sh", "fish", "posix"}:
        return "posix"
    if guessed in {"powershell", "pwsh", "ps"}:
        return "powershell"
    if guessed in {"cmd", "cmd.exe"}:
        return "cmd"
    return guessed if guessed in {"posix", "powershell", "cmd"} else "unknown"


def setup_commands(name: str, shell: str | None = None, value: str = "your-key") -> list[str]:
    env_name = require_valid_env_var_name(name)
    target = normalize_shell(shell)
    if target == "powershell":
        quoted = _quote_powershell(value)
        return [
            f"$env:{env_name}={quoted}",
            f'[Environment]::SetEnvironmentVariable("{env_name}", {quoted}, "User")',
        ]
    if target == "cmd":
        return [
            f"set {env_name}={value}",
            f"setx {env_name} {_quote_cmd(value)}",
        ]
    if target == "unknown":
        return [
            f"PowerShell: $env:{env_name}={_quote_powershell(value)}",
            f"cmd.exe: set {env_name}={value}",
            f"bash/zsh: export {env_name}={_quote_posix(value)}",
        ]
    quoted = _quote_posix(value)
    return [
        f"export {env_name}={quoted}",
        f"echo 'export {env_name}={quoted}' >> ~/.zshrc",
    ]
