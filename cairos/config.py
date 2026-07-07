"""Persistent CAIROS configuration.

CAIROS stores global settings in ``~/.config/cairos/config.json`` so the tool can
"live in the console" and support any project directory.  Project-specific
rules are handled separately in ``rules.py``.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "ai": {
        "provider": "none",
        "model": "",
        "endpoint": "",
        "api_key_env": "OPENAI_API_KEY",
        "custom_command": "",
        "timeout_seconds": 60,
        "auto_fallback": True,
        "fallback_order": [],
        "fallback_persist_switch": True,
    },
    "ai_profiles": {},
    "active_ai_profile": "",
    "behavior": {
        "require_confirmation": True,
        "send_context_to_ai": True,
        "max_context_files": 80,
        "default_confirmation_phrase": "yes",
        "template_confidence_threshold": 0.8,
        "ai_on_uncertain_template": True,
        "ai_router_enabled": False,
        "router": "auto",
        "ml_router_enabled": False,
    },
}


class ConfigError(RuntimeError):
    """Raised when the CAIROS config file cannot be loaded safely."""


def config_dir(system: str | None = None) -> Path:
    """Return the global CAIROS config directory for the current platform."""
    system_name = system or platform.system()
    if system_name == "Windows":
        return Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "cairos"
    return Path.home() / ".config" / "cairos"


def state_dir(system: str | None = None) -> Path:
    """Return the global CAIROS state directory for the current platform."""
    system_name = system or platform.system()
    if system_name == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "cairos"
    return Path.home() / ".local" / "state" / "cairos"


def config_path() -> Path:
    """Return the global CAIROS config path."""
    return config_dir() / "config.json"


def shell_guess(system: str | None = None, environ: dict[str, str] | None = None) -> str:
    """Return a friendly shell guess for setup hints."""
    return detect_shell_kind(system=system, environ=environ)


def detect_shell_kind(system: str | None = None, environ: dict[str, str] | None = None) -> str:
    """Return ``cmd``, ``powershell``, ``posix`` or ``unknown``."""
    env = os.environ if environ is None else environ
    override = env.get("CAIROS_SHELL", "").lower()
    if override in {"cmd", "cmd.exe"}:
        return "cmd"
    if override in {"powershell", "pwsh", "ps"}:
        return "powershell"
    if override in {"bash", "zsh", "fish", "sh", "posix"}:
        return "posix"

    system_name = system or platform.system()
    if system_name == "Windows":
        comspec = env.get("ComSpec", "").lower()
        if "cmd.exe" in comspec:
            return "cmd"
        if env.get("TERM_PROGRAM", "").lower() in {"vscode", "windows terminal"} and env.get("PSModulePath"):
            return "unknown"
        if env.get("PWSH") or env.get("POWERSHELL_DISTRIBUTION_CHANNEL"):
            return "powershell"
        return "unknown"
    shell = Path(env.get("SHELL", "")).name.lower()
    if shell in {"bash", "zsh", "fish", "sh"}:
        return "posix"
    return "posix" if shell else "unknown"


def env_var_hint(name: str, shell: str | None = None) -> list[str]:
    """Return shell-specific commands for setting an environment variable."""
    guessed = (shell or detect_shell_kind()).lower()
    if guessed == "powershell":
        return [
            f'$env:{name}="your-key"',
            f'[Environment]::SetEnvironmentVariable("{name}", "your-key", "User")',
        ]
    if guessed == "cmd":
        return [
            f"set {name}=your-key",
            f'setx {name} "your-key"',
        ]
    if guessed == "unknown-windows" or (guessed == "unknown" and platform.system() == "Windows"):
        return [
            f"cmd.exe: set {name}=your-key",
            f'cmd.exe: setx {name} "your-key"',
            f'PowerShell: $env:{name}="your-key"',
            f'PowerShell: [Environment]::SetEnvironmentVariable("{name}", "your-key", "User")',
        ]
    return [f'export {name}="your-key"']


def env_var_setup_hint(name: str, shell_kind: str | None = None) -> str:
    """Return a user-facing shell-specific environment setup block."""
    guessed = (shell_kind or detect_shell_kind()).lower()
    if guessed == "cmd":
        return (
            f"For this cmd.exe session:\n"
            f"  set {name}=your-key\n\n"
            f"Persist for future cmd.exe sessions:\n"
            f"  setx {name} \"your-key\""
        )
    if guessed == "powershell":
        return (
            f"For this PowerShell session:\n"
            f"  $env:{name}=\"your-key\"\n\n"
            f"Persist for future PowerShell sessions:\n"
            f"  [Environment]::SetEnvironmentVariable(\"{name}\", \"your-key\", \"User\")"
        )
    if guessed == "unknown-windows" or (guessed == "unknown" and platform.system() == "Windows"):
        return (
            f"For cmd.exe:\n"
            f"  set {name}=your-key\n"
            f"  setx {name} \"your-key\"\n\n"
            f"For PowerShell:\n"
            f"  $env:{name}=\"your-key\"\n"
            f"  [Environment]::SetEnvironmentVariable(\"{name}\", \"your-key\", \"User\")"
        )
    return (
        f"For this shell session:\n"
        f"  export {name}=\"your-key\"\n\n"
        "Persist by adding it to your shell profile or a sourced secrets file."
    )


def _clone_default() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_config() -> Path | None:
    """Copy the current config file to a timestamped backup, if it exists."""
    path = config_path()
    if not path.exists():
        return None
    backup = path.with_name(f"config.backup-{_timestamp()}.json")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"config.backup-{_timestamp()}-{counter}.json")
        counter += 1
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    return backup


def _atomic_write_json(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def migrate_config(config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return config merged with defaults and whether it changed."""
    if not isinstance(config, dict):
        config = {}
    merged = _deep_merge(DEFAULT_CONFIG, config)
    raw_version = config.get("schema_version", config.get("config_version", 0))
    try:
        version = int(raw_version)
    except (TypeError, ValueError):
        version = 0
    merged["schema_version"] = SCHEMA_VERSION
    changed = merged != config or version != SCHEMA_VERSION
    return merged, changed


def migrate_config_file() -> tuple[Path, Path | None, bool]:
    """Apply config migrations now and return path, backup path and changed flag."""
    path = config_path()
    if not path.exists():
        save_config(_clone_default())
        return path, None, True
    try:
        user_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Could not read CAIROS config because it is not valid JSON: {path}\n"
            f"JSON error: {exc}\n"
            "The file was not overwritten. Restore a config.backup-*.json file or fix the JSON and retry."
        ) from exc
    migrated, changed = migrate_config(user_config if isinstance(user_config, dict) else {})
    backup = None
    if changed:
        backup = backup_config()
        _atomic_write_json(path, migrated)
    return path, backup, changed


def load_config() -> dict[str, Any]:
    """Load config, migrate it if needed, and merge it with defaults."""
    path = config_path()
    if not path.exists():
        return _clone_default()
    try:
        user_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Could not read CAIROS config because it is not valid JSON: {path}\n"
            f"JSON error: {exc}\n"
            "The file was not overwritten. Restore a config.backup-*.json file or fix the JSON and retry."
        ) from exc
    migrated, changed = migrate_config(user_config if isinstance(user_config, dict) else {})
    if changed:
        backup_config()
        _atomic_write_json(path, migrated)
    return migrated


def save_config(config: dict[str, Any]) -> Path:
    """Write the global config file atomically, preserving default keys."""
    path = config_path()
    merged, _ = migrate_config(config)
    _atomic_write_json(path, merged)
    return path


def _parse_value(raw_value: str) -> Any:
    lowered = raw_value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(raw_value)
    except ValueError:
        return raw_value


def set_config_value(key_path: str, raw_value: str) -> Path:
    """Set a dotted config key, for example ``ai.provider``."""
    config = load_config()
    keys = key_path.split(".")
    current = config
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = _parse_value(raw_value)
    return save_config(config)


def _sanitize_profile_name(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-._")
    return clean or "default"


def _profile_default_name(provider: str, model: str = "") -> str:
    if provider == "custom-command":
        return "custom-command"
    suffix = re.sub(r"[^A-Za-z0-9_.-]+", "-", model or provider).strip("-")
    return _sanitize_profile_name(f"{provider}-{suffix}")


def _profile_from_ai(ai: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": ai.get("provider", "none"),
        "model": ai.get("model", ""),
        "endpoint": ai.get("endpoint", ""),
        "api_key_env": ai.get("api_key_env", ""),
        "custom_command": ai.get("custom_command", ""),
        "timeout_seconds": ai.get("timeout_seconds", 60),
    }


def _set_active_profile(config: dict[str, Any], name: str, profile: dict[str, Any]) -> None:
    safe_name = _sanitize_profile_name(name)
    config.setdefault("ai_profiles", {})[safe_name] = _profile_from_ai(profile)
    config["active_ai_profile"] = safe_name
    config["ai"].update(config["ai_profiles"][safe_name])


def save_current_ai_profile(name: str) -> Path:
    config = load_config()
    safe_name = _sanitize_profile_name(name)
    config.setdefault("ai_profiles", {})[safe_name] = _profile_from_ai(config["ai"])
    config["active_ai_profile"] = safe_name
    return save_config(config)


def activate_ai_profile(name: str) -> Path:
    config = load_config()
    safe_name = _sanitize_profile_name(name)
    profiles = config.setdefault("ai_profiles", {})
    if safe_name not in profiles:
        raise KeyError(safe_name)
    config["active_ai_profile"] = safe_name
    config["ai"].update(profiles[safe_name])
    return save_config(config)


def delete_ai_profile(name: str, force: bool = False) -> Path:
    config = load_config()
    safe_name = _sanitize_profile_name(name)
    active = config.get("active_ai_profile", "")
    if safe_name == active and not force:
        raise ValueError("active")
    profiles = config.setdefault("ai_profiles", {})
    if safe_name not in profiles:
        raise KeyError(safe_name)
    profiles.pop(safe_name)
    if safe_name == active:
        config["active_ai_profile"] = ""
    return save_config(config)


def rename_ai_profile(old: str, new: str) -> Path:
    config = load_config()
    old_name = _sanitize_profile_name(old)
    new_name = _sanitize_profile_name(new)
    profiles = config.setdefault("ai_profiles", {})
    if old_name not in profiles:
        raise KeyError(old_name)
    profiles[new_name] = profiles.pop(old_name)
    if config.get("active_ai_profile") == old_name:
        config["active_ai_profile"] = new_name
    return save_config(config)


def update_ai_profile(name: str, new_name: str, model: str, endpoint: str, api_key_env: str) -> Path:
    """Update editable fields for an existing AI profile."""
    config = load_config()
    old_name = _sanitize_profile_name(name)
    target_name = _sanitize_profile_name(new_name or name)
    profiles = config.setdefault("ai_profiles", {})
    if old_name not in profiles:
        raise KeyError(old_name)
    profile = dict(profiles.pop(old_name))
    profile["model"] = model
    profile["endpoint"] = endpoint
    profile["api_key_env"] = api_key_env
    profiles[target_name] = _profile_from_ai(profile)
    if config.get("active_ai_profile") == old_name:
        config["active_ai_profile"] = target_name
        config["ai"].update(profiles[target_name])
    return save_config(config)


def ai_profiles() -> dict[str, dict[str, Any]]:
    config = load_config()
    return config.setdefault("ai_profiles", {})


def active_ai_profile_name() -> str:
    return str(load_config().get("active_ai_profile", ""))


def ai_fallback_settings() -> dict[str, Any]:
    """Return normalized AI fallback settings."""
    ai = load_config()["ai"]
    order = ai.get("fallback_order", [])
    if not isinstance(order, list):
        order = []
    return {
        "auto_fallback": bool(ai.get("auto_fallback", True)),
        "fallback_order": [str(item) for item in order],
        "fallback_persist_switch": bool(ai.get("fallback_persist_switch", True)),
    }


def set_ai_fallback(enabled: bool | None = None, order: list[str] | None = None, persist_switch: bool | None = None) -> Path:
    """Update global AI fallback settings."""
    config = load_config()
    ai = config.setdefault("ai", {})
    if enabled is not None:
        ai["auto_fallback"] = enabled
    if order is not None:
        ai["fallback_order"] = [_sanitize_profile_name(name) for name in order]
    if persist_switch is not None:
        ai["fallback_persist_switch"] = persist_switch
    return save_config(config)


def configure_ollama(model: str = "llama3.1", endpoint: str = "http://localhost:11434", profile: str | None = None) -> Path:
    """Configure CAIROS to use a local Ollama model."""
    config = load_config()
    config["ai"].update({"provider": "ollama", "model": model, "endpoint": endpoint, "api_key_env": "", "custom_command": ""})
    _set_active_profile(config, profile or _profile_default_name("ollama", model), config["ai"])
    return save_config(config)


def configure_openai(model: str = "gpt-4.1-mini", api_key_env: str = "OPENAI_API_KEY", endpoint: str = "https://api.openai.com/v1", profile: str | None = None) -> Path:
    """Configure an OpenAI-compatible chat completions endpoint."""
    config = load_config()
    config["ai"].update({"provider": "openai", "model": model, "endpoint": endpoint, "api_key_env": api_key_env, "custom_command": ""})
    _set_active_profile(config, profile or _profile_default_name("openai", model), config["ai"])
    return save_config(config)


def configure_gemini(model: str = "gemini-2.5-flash", api_key_env: str = "GEMINI_API_KEY", profile: str | None = None) -> Path:
    """Configure CAIROS to use Google's Gemini API without storing the key."""
    config = load_config()
    config["ai"].update({"provider": "gemini", "model": model, "endpoint": "https://generativelanguage.googleapis.com/v1beta", "api_key_env": api_key_env, "custom_command": ""})
    _set_active_profile(config, profile or _profile_default_name("gemini", model), config["ai"])
    return save_config(config)


def configure_custom_command(command: str, profile: str | None = None) -> Path:
    """Configure a local command that reads JSON from stdin and writes plan JSON."""
    config = load_config()
    config["ai"].update({"provider": "custom-command", "model": "", "endpoint": "", "api_key_env": "", "custom_command": command})
    _set_active_profile(config, profile or "custom-command", config["ai"])
    return save_config(config)


def disable_ai() -> Path:
    """Disable AI fallback and use deterministic templates only."""
    config = load_config()
    config["ai"]["provider"] = "none"
    config["active_ai_profile"] = ""
    return save_config(config)


def config_json() -> str:
    """Return the active config as pretty JSON."""
    return json.dumps(load_config(), indent=2, sort_keys=True)


def ai_status() -> str:
    """Return a human-readable AI backend status without exposing secrets."""
    config = load_config()
    ai = config["ai"]
    provider = ai.get("provider", "none")
    lines = ["AI configuration:", f"provider: {provider}"]
    active_profile = config.get("active_ai_profile", "")
    if active_profile:
        lines.append(f"active_profile: {active_profile}")
    fallback = ai_fallback_settings()
    order = ", ".join(fallback["fallback_order"]) or "<default>"
    lines.append(f"auto_fallback: {'enabled' if fallback['auto_fallback'] else 'disabled'}")
    lines.append(f"fallback_order: {order}")
    lines.append(f"fallback_persist_switch: {'yes' if fallback['fallback_persist_switch'] else 'no'}")
    if provider == "none":
        openai_hint = " && ".join(env_var_hint("OPENAI_API_KEY"))
        lines.extend([
            "status: no AI backend configured",
            "local setup: cairos config ai use-ollama llama3.1",
            f"api setup: {openai_hint} && cairos config ai use-openai gpt-4.1-mini",
        ])
    elif provider == "ollama":
        lines.append(f"model: {ai.get('model') or 'llama3.1'}")
        lines.append(f"endpoint: {ai.get('endpoint') or 'http://localhost:11434'}")
        lines.append("hint: run `ollama serve` and `ollama pull <model>` if needed")
    elif provider in {"openai", "openai-compatible"}:
        env_name = ai.get("api_key_env") or "OPENAI_API_KEY"
        lines.append(f"model: {ai.get('model') or '<not set>'}")
        lines.append(f"endpoint: {ai.get('endpoint') or 'https://api.openai.com/v1'}")
        lines.append(f"api_key_env: {env_name}")
        lines.append(f"api_key_available: {'yes' if os.environ.get(env_name) else 'no'}")
    elif provider == "gemini":
        env_name = ai.get("api_key_env") or "GEMINI_API_KEY"
        lines.append(f"model: {ai.get('model') or 'gemini-2.5-flash'}")
        lines.append(f"endpoint: {ai.get('endpoint') or 'https://generativelanguage.googleapis.com/v1beta'}")
        lines.append(f"api_key_env: {env_name}")
        lines.append(f"api_key_available: {'yes' if os.environ.get(env_name) else 'no'}")
        lines.append("hint: run `cairos config ai list-models` if the configured model is unavailable")
    elif provider == "custom-command":
        lines.append(f"custom_command: {ai.get('custom_command') or '<not set>'}")
        lines.append("contract: command reads CAIROS JSON from stdin and prints plan JSON to stdout")
    else:
        lines.append("status: unsupported provider configured")
    lines.append(f"config_path: {config_path()}")
    return "\n".join(lines)
