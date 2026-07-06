from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_RULES: dict[str, Any] = {
    "project": {"type": "auto"},
    "python": {
        "layout": "package",
        "use_pyproject": True,
        "test_dir": "tests",
    },
    "cpp": {
        "header_style": "ifndef",
        "header_extension": ".hpp",
        "source_extension": ".cpp",
        "include_dir": "include",
        "source_dir": "src",
        "test_dir": "tests",
        "class_constructors": True,
        "namespace": "",
    },
    "git": {
        "main_branch": "main",
        "remote": "origin",
        "force_push_allowed": False,
    },
}


def global_rules_path() -> Path:
    return Path.home() / ".config" / "cairos" / "rules.json"


def local_rules_path() -> Path:
    return Path.cwd() / ".cairos" / "rules.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_rules() -> dict[str, Any]:
    rules = DEFAULT_RULES
    rules = _deep_merge(rules, _read_json(global_rules_path()))
    rules = _deep_merge(rules, _read_json(local_rules_path()))
    return rules


def init_local_rules() -> Path:
    path = local_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_RULES, indent=2) + "\n", encoding="utf-8")
    return path


def rules_json() -> str:
    return json.dumps(load_rules(), indent=2, sort_keys=True)


def set_rule(key_path: str, raw_value: str, local: bool = True) -> Path:
    path = local_rules_path() if local else global_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)
    keys = key_path.split(".")
    current = data
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    value: Any = raw_value
    if raw_value.lower() in {"true", "false"}:
        value = raw_value.lower() == "true"
    else:
        try:
            value = int(raw_value)
        except ValueError:
            value = raw_value
    current[keys[-1]] = value
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
