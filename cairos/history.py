"""History storage for CAIROS commands.

History lives in ``~/.local/state/cairos/history.jsonl`` and stores compact
metadata only.  It deliberately avoids command output, file contents and secret
values.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import state_dir


def history_path() -> Path:
    """Return the global history file path."""
    return state_dir() / "history.jsonl"


def append_history(request: str, source: str, risk: str, executed: bool, exit_code: int, cwd: str | None = None) -> Path:
    """Append one sanitized history record."""
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cwd": cwd or str(Path.cwd()),
        "request": request[:500],
        "source": source,
        "risk": risk,
        "executed": executed,
        "exit_code": exit_code,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def read_history(limit: int | None = None) -> list[dict[str, Any]]:
    """Read history records, newest last."""
    path = history_path()
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records[-limit:] if limit else records


def clear_history() -> Path:
    """Remove history entries by replacing the file with an empty one."""
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def format_history(limit: int | None = None) -> str:
    """Return a concise human-readable history listing."""
    records = read_history(limit)
    if not records:
        return f"No CAIROS history yet.\npath: {history_path()}"
    lines = [f"History path: {history_path()}"]
    for record in records:
        lines.append(
            f"{record.get('timestamp', '?')} | {record.get('risk', '?')} | "
            f"executed={record.get('executed', False)} exit={record.get('exit_code', '?')} | "
            f"{record.get('request', '')}"
        )
    return "\n".join(lines)
