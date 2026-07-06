from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

IGNORED_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache", "dist", "build", ".mypy_cache"}
SECRET_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}


def _run(command: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=3)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except Exception as exc:  # pragma: no cover - defensive fallback
        return 1, str(exc)


def _is_git_repo(cwd: Path) -> bool:
    code, _ = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return code == 0


def _git_context(cwd: Path) -> dict[str, Any]:
    if not _is_git_repo(cwd):
        return {"is_repo": False}

    def git(*args: str) -> str:
        return _run(["git", *args], cwd)[1]

    status = git("status", "--short")
    branch = git("branch", "--show-current") or "detached"
    remote = git("remote")
    remotes = [line for line in remote.splitlines() if line.strip()]
    log = git("log", "--oneline", "--decorate", "--max-count=8")
    return {
        "is_repo": True,
        "branch": branch,
        "dirty": bool(status.strip()),
        "status_short": status.splitlines()[:30],
        "remotes": remotes,
        "log_recent": log.splitlines()[:8],
    }


def _detect_project_type(cwd: Path) -> str:
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists() or any(cwd.glob("*.py")):
        return "python"
    if (cwd / "CMakeLists.txt").exists() or any(cwd.glob("*.cpp")) or any(cwd.glob("*.hpp")) or (cwd / "include").exists():
        return "cpp"
    if (cwd / "package.json").exists():
        return "node"
    if (cwd / "Cargo.toml").exists():
        return "rust"
    return "unknown"


def _compact_tree(cwd: Path, max_entries: int = 60, max_depth: int = 2) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    root_depth = len(cwd.parts)
    for path in sorted(cwd.rglob("*"), key=lambda p: str(p).lower()):
        rel = path.relative_to(cwd)
        if any(part in IGNORED_DIRS for part in rel.parts):
            if path.is_dir():
                continue
            continue
        if path.name in SECRET_NAMES or path.name.startswith(".env"):
            continue
        depth = len(path.parts) - root_depth
        if depth > max_depth:
            continue
        entries.append({"path": str(rel), "type": "dir" if path.is_dir() else "file"})
        if len(entries) >= max_entries:
            break
    return entries


def collect_context(max_files: int = 60) -> dict[str, Any]:
    cwd = Path.cwd()
    return {
        "cwd": str(cwd),
        "shell": os.environ.get("SHELL", "unknown"),
        "system": platform.system(),
        "release": platform.release(),
        "project_type": _detect_project_type(cwd),
        "git": _git_context(cwd),
        "files": _compact_tree(cwd, max_entries=max_files),
    }


def context_json() -> str:
    return json.dumps(collect_context(), indent=2, sort_keys=True)


def context_summary() -> str:
    context = collect_context(max_files=20)
    git = context["git"]
    lines = [
        f"cwd: {context['cwd']}",
        f"shell: {context['shell']}",
        f"system: {context['system']} {context['release']}",
        f"project_type: {context['project_type']}",
    ]
    if git.get("is_repo"):
        lines.append(f"git: branch={git.get('branch')} dirty={'yes' if git.get('dirty') else 'no'} remotes={','.join(git.get('remotes', [])) or 'none'}")
    else:
        lines.append("git: not a repository")
    return "\n".join(lines)
