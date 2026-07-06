"""Compact project and shell context collection for templates and AI prompts.

The context collector avoids secrets and common large directories so CAIROS can
provide useful big-picture information without dumping an entire repository.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".cache",
    ".idea",
    ".vscode",
    "build",
    "dist",
    "target",
    ".tox",
    ".nox",
    "site-packages",
    "AppData",
    "pipx",
    ".local",
    "OneDrive",
    "Library",
}
IGNORED_DIRS_LOWER = {name.lower() for name in IGNORED_DIRS}
PROJECT_MARKERS = {
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "CMakeLists.txt",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "README.md",
    "Makefile",
}
SECRET_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".pem", ".key"}


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
    remote_url = git("remote", "get-url", "origin") if "origin" in remotes else ""
    origin_main = git("rev-parse", "--verify", "--quiet", "origin/main")
    log = git("log", "--oneline", "--decorate", "--max-count=8")
    return {
        "is_repo": True,
        "branch": branch,
        "dirty": bool(status.strip()),
        "status_short": status.splitlines()[:30],
        "remotes": remotes,
        "remote_url": remote_url,
        "origin_main_available": bool(origin_main.strip()),
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


def _detect_package_manager(cwd: Path) -> str:
    if (cwd / "uv.lock").exists():
        return "uv"
    if (cwd / "poetry.lock").exists():
        return "poetry"
    if (cwd / "package-lock.json").exists():
        return "npm"
    if (cwd / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (cwd / "yarn.lock").exists():
        return "yarn"
    if (cwd / "Cargo.toml").exists():
        return "cargo"
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists():
        return "pip"
    return "unknown"


def _detect_test_command(cwd: Path) -> str:
    if (cwd / "Makefile").exists():
        return "make test"
    if (cwd / "package.json").exists():
        return "npm test"
    if (cwd / "Cargo.toml").exists():
        return "cargo test"
    if (cwd / "pyproject.toml").exists() or (cwd / "requirements.txt").exists() or any(cwd.glob("tests/test_*.py")):
        return "python -m pytest"
    if (cwd / "CMakeLists.txt").exists():
        return "cmake --build build && ctest --test-dir build"
    return "unknown"


def _is_home_dir(cwd: Path) -> bool:
    """Return True when cwd is the current user home directory."""
    try:
        return cwd.resolve() == Path.home().resolve()
    except (OSError, RuntimeError):
        return cwd == Path.home()


def looks_like_project_root(cwd: Path) -> bool:
    """Return True when cwd has direct project marker files/directories."""
    for marker in PROJECT_MARKERS:
        try:
            if (cwd / marker).exists():
                return True
        except OSError:
            continue
    return False


def _entry_type(path: Path) -> str:
    """Return a safe file type label without raising on broken paths."""
    try:
        if path.is_dir() and not path.is_symlink():
            return "dir"
        if path.is_file():
            return "file"
    except OSError:
        return "unknown"
    return "unknown"


def _should_ignore(path: Path) -> bool:
    """Return True when an entry should be skipped before descent."""
    try:
        name = path.name
        if name.lower() in IGNORED_DIRS_LOWER:
            return True
        if name in SECRET_NAMES or name.startswith(".env") or path.suffix in SECRET_SUFFIXES:
            return True
        if path.is_symlink() and path.is_dir():
            return True
    except OSError:
        return True
    return False


def _format_entry(cwd: Path, path: Path) -> dict[str, str] | None:
    """Return a context tree entry for path, or None if it cannot be represented."""
    try:
        rel = path.relative_to(cwd)
    except (RuntimeError, ValueError):
        return None
    entry_type = _entry_type(path)
    if entry_type == "unknown":
        return None
    rel_path = str(rel).replace("\\", "/")
    if entry_type == "dir":
        rel_path += "/"
    return {"path": rel_path, "type": entry_type}


def _safe_sorted_children(path: Path) -> list[Path]:
    """List direct children safely, directories first, without following junctions."""
    try:
        entries = list(path.iterdir())
    except (PermissionError, OSError):
        return []
    return sorted(entries, key=lambda p: (_entry_type(p) != "dir", p.name.lower()))


def _compact_tree(
    cwd: Path,
    max_entries: int = 60,
    max_depth: int = 3,
    max_dirs_scanned: int = 200,
    max_seconds: float = 1.0,
) -> list[dict[str, str]]:
    """Return a bounded recursive file tree for project roots.

    This intentionally avoids full recursive tree materialization. Limits are
    enforced during traversal.
    """
    results: list[dict[str, str]] = []
    dirs_scanned = 0
    started = time.monotonic()

    def timed_out() -> bool:
        return time.monotonic() - started > max_seconds

    def walk(path: Path, depth: int) -> None:
        nonlocal dirs_scanned
        if len(results) >= max_entries or dirs_scanned >= max_dirs_scanned or depth > max_depth or timed_out():
            return
        children = _safe_sorted_children(path)
        dirs_scanned += 1
        for child in children:
            if len(results) >= max_entries or dirs_scanned >= max_dirs_scanned or timed_out():
                return
            if _should_ignore(child):
                continue
            item = _format_entry(cwd, child)
            if item is None:
                continue
            results.append(item)
            if item["type"] == "dir" and depth < max_depth:
                walk(child, depth + 1)

    walk(cwd, 0)
    return results


def _shallow_tree(cwd: Path, max_entries: int = 40) -> list[dict[str, str]]:
    """Return a safe direct-child listing for home and non-project folders."""
    results: list[dict[str, str]] = []
    for child in _safe_sorted_children(cwd):
        if len(results) >= max_entries:
            break
        if _should_ignore(child):
            continue
        item = _format_entry(cwd, child)
        if item is not None:
            results.append(item)
    return results


def collect_context(max_files: int = 60) -> dict[str, Any]:
    cwd = Path.cwd()
    if _is_home_dir(cwd):
        files = _shallow_tree(cwd, max_entries=min(max_files, 40))
        scan_note = "home directory: recursive file scan skipped"
    elif looks_like_project_root(cwd):
        files = _compact_tree(cwd, max_entries=max_files)
        scan_note = ""
    else:
        files = _shallow_tree(cwd, max_entries=min(max_files, 40))
        scan_note = "non-project directory: recursive file scan limited"
    return {
        "cwd": str(cwd),
        "shell": os.environ.get("SHELL", "unknown"),
        "system": platform.system(),
        "release": platform.release(),
        "project_type": _detect_project_type(cwd),
        "package_manager": _detect_package_manager(cwd),
        "test_command": _detect_test_command(cwd),
        "git": _git_context(cwd),
        "files": files,
        "file_tree_note": scan_note,
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
        f"package_manager: {context['package_manager']}",
        f"test_command: {context['test_command']}",
    ]
    if git.get("is_repo"):
        lines.append(f"git: branch={git.get('branch')} dirty={'yes' if git.get('dirty') else 'no'} remotes={','.join(git.get('remotes', [])) or 'none'} origin/main={'yes' if git.get('origin_main_available') else 'no'}")
    else:
        lines.append("git: not a repository")
    if context.get("file_tree_note"):
        lines.append(f"file_tree: {context['file_tree_note']}")
    return "\n".join(lines)
