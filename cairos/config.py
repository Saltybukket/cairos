"""Persistent CAIROS configuration.

CAIROS stores global settings in ``~/.config/cairos/config.json`` so the tool can
"live in the console" and support any project directory.  Project-specific
rules are handled separately in ``rules.py``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "ai": {
        "provider": "none",
        "model": "",
        "endpoint": "",
        "api_key_env": "OPENAI_API_KEY",
        "custom_command": "",
        "timeout_seconds": 60,
    },
    "behavior": {
        "require_confirmation": True,
        "send_context_to_ai": True,
        "max_context_files": 80,
        "default_confirmation_phrase": "yes",
    },
}


def config_path() -> Path:
    """Return the global CAIROS config path."""
    return Path.home() / ".config" / "cairos" / "config.json"


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


def load_config() -> dict[str, Any]:
    """Load config and merge it with defaults."""
    path = config_path()
    if not path.exists():
        return _clone_default()
    try:
        user_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _clone_default()
    return _deep_merge(DEFAULT_CONFIG, user_config if isinstance(user_config, dict) else {})


def save_config(config: dict[str, Any]) -> Path:
    """Write the global config file."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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


def configure_ollama(model: str = "llama3.1", endpoint: str = "http://localhost:11434") -> Path:
    """Configure CAIROS to use a local Ollama model."""
    config = load_config()
    config["ai"].update({"provider": "ollama", "model": model, "endpoint": endpoint})
    return save_config(config)


def configure_openai(model: str = "gpt-4.1-mini", api_key_env: str = "OPENAI_API_KEY", endpoint: str = "https://api.openai.com/v1") -> Path:
    """Configure an OpenAI-compatible chat completions endpoint."""
    config = load_config()
    config["ai"].update({"provider": "openai", "model": model, "endpoint": endpoint, "api_key_env": api_key_env})
    return save_config(config)


def configure_gemini(model: str = "gemini-1.5-flash", api_key_env: str = "GEMINI_API_KEY") -> Path:
    """Configure CAIROS to use Google's Gemini API without storing the key."""
    config = load_config()
    config["ai"].update({"provider": "gemini", "model": model, "endpoint": "https://generativelanguage.googleapis.com/v1beta", "api_key_env": api_key_env})
    return save_config(config)


def configure_custom_command(command: str) -> Path:
    """Configure a local command that reads JSON from stdin and writes plan JSON."""
    config = load_config()
    config["ai"].update({"provider": "custom-command", "custom_command": command})
    return save_config(config)


def disable_ai() -> Path:
    """Disable AI fallback and use deterministic templates only."""
    config = load_config()
    config["ai"]["provider"] = "none"
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
    if provider == "none":
        lines.extend([
            "status: no AI backend configured",
            "local setup: cairos config ai use-ollama llama3.1",
            "api setup: export OPENAI_API_KEY=... && cairos config ai use-openai gpt-4.1-mini",
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
        lines.append(f"model: {ai.get('model') or 'gemini-1.5-flash'}")
        lines.append(f"endpoint: {ai.get('endpoint') or 'https://generativelanguage.googleapis.com/v1beta'}")
        lines.append(f"api_key_env: {env_name}")
        lines.append(f"api_key_available: {'yes' if os.environ.get(env_name) else 'no'}")
    elif provider == "custom-command":
        lines.append(f"custom_command: {ai.get('custom_command') or '<not set>'}")
        lines.append("contract: command reads CAIROS JSON from stdin and prints plan JSON to stdout")
    else:
        lines.append("status: unsupported provider configured")
    lines.append(f"config_path: {config_path()}")
    return "\n".join(lines)
