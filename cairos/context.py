import json
import os
import platform
from pathlib import Path


def collect_context(max_files: int = 25) -> dict:
    cwd = Path.cwd()
    files = []
    for path in sorted(cwd.iterdir(), key=lambda p: p.name.lower()):
        if path.name.startswith(".env"):
            continue
        files.append({"name": path.name, "type": "dir" if path.is_dir() else "file"})
        if len(files) >= max_files:
            break
    return {
        "cwd": str(cwd),
        "shell": os.environ.get("SHELL", "unknown"),
        "system": platform.system(),
        "release": platform.release(),
        "files": files,
    }


def context_json() -> str:
    return json.dumps(collect_context(), indent=2, sort_keys=True)
