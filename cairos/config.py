from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "ai": {
        "provider": "none",
        "model": "",
        "endpoint": "",
        "api_key_env": "OPENAI_API_KEY",
        "custom_command": "",
    },
    "behavior": {
        "require_confirmation": True,
        "send_context_to_ai": True,
    },
}


def config_path() -> Path:
    return Path.home() / ".config" / "cairos" / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        user_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    return _deep_merge(DEFAULT_CONFIG, user_config if isinstance(user_config, dict) else {})


def save_config(config: dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def set_config_value(key_path: str, raw_value: str) -> Path:
    config = load_config()
    keys = key_path.split(".")
    current = config
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    if raw_value.lower() in {"true", "false"}:
        value: Any = raw_value.lower() == "true"
    else:
        value = raw_value
    current[keys[-1]] = value
    return save_config(config)


def config_json() -> str:
    return json.dumps(load_config(), indent=2, sort_keys=True)


def ai_status() -> str:
    config = load_config()
    ai = config["ai"]
    provider = ai.get("provider", "none")
    lines = ["AI configuration:", f"provider: {provider}"]
    if provider == "none":
        lines.append("status: no AI backend configured")
        lines.append("hint: cairos config ai set-provider ollama")
    else:
        lines.append(f"model: {ai.get('model') or '<not set>'}")
        lines.append(f"endpoint: {ai.get('endpoint') or '<default>'}")
        if provider == "openai":
            lines.append(f"api_key_env: {ai.get('api_key_env')}")
    return "\n".join(lines)
