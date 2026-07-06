"""Deterministic command explanations with context-aware safety notes."""

from __future__ import annotations

from .context import context_summary
from .safety import check_command


def explain_command(command: str, include_context: bool = True) -> str:
    lowered = command.strip().lower()
    safety = check_command(command)
    lines = [f"Command: {command}", "Meaning:"]

    if lowered.startswith("git reset --soft"):
        lines.append("Moves the current branch pointer, but keeps changes staged/in the index.")
        lines.append("Useful for rewriting the last commit without losing file changes.")
    elif lowered.startswith("git reset --hard"):
        lines.append("Moves the current branch pointer and discards matching working tree changes.")
        lines.append("This can permanently lose uncommitted work.")
    elif lowered.startswith("git fetch"):
        lines.append("Downloads remote branch information without merging it into your current branch.")
    elif lowered.startswith("git pull"):
        lines.append("Fetches remote changes and integrates them into the current branch, usually by merge.")
    elif lowered.startswith("git merge"):
        lines.append("Combines another branch into the current branch and may create a merge commit.")
    elif lowered.startswith("git rebase"):
        lines.append("Replays commits on top of another base commit. This rewrites local commit history.")
    elif lowered.startswith("git status"):
        lines.append("Shows branch state and changed files in the working tree and index.")
    elif lowered.startswith("git log"):
        lines.append("Shows commit history.")
    elif lowered.startswith("git push"):
        lines.append("Uploads local commits to a remote repository branch.")
    elif lowered.startswith("rm"):
        lines.append("Removes files or directories. Recursive or force options increase risk.")
    elif lowered.startswith("cp"):
        lines.append("Copies files or directories.")
    elif lowered.startswith("mv"):
        lines.append("Moves or renames files and directories.")
    elif lowered.startswith("find"):
        lines.append("Searches files/directories according to filters. Actions like -delete or -exec rm modify files.")
    elif lowered.startswith("grep"):
        lines.append("Searches text input or files for matching patterns.")
    elif lowered.startswith("chmod"):
        lines.append("Changes file permissions.")
    elif lowered.startswith("chown"):
        lines.append("Changes file ownership.")
    elif lowered.startswith("python3 -m venv") or lowered.startswith("python -m venv"):
        lines.append("Creates a Python virtual environment in the target directory.")
    elif lowered.startswith("mkdir"):
        lines.append("Creates one or more directories.")
    elif lowered.startswith("touch"):
        lines.append("Creates files if missing or updates timestamps if they already exist.")
    elif lowered.startswith("pip install") or lowered.startswith("python -m pip install") or lowered.startswith("python3 -m pip install"):
        lines.append("Installs Python packages into the active environment.")
    elif lowered.startswith("make"):
        lines.append("Runs a Makefile target, or the default target if none is given.")
    elif lowered.startswith("cmake"):
        lines.append("Configures or builds a C/C++ project using CMake.")
    elif lowered.startswith("npm install"):
        lines.append("Installs Node dependencies and updates lockfiles when needed.")
    elif lowered.startswith("cargo build"):
        lines.append("Builds a Rust package with Cargo.")
    else:
        lines.append("No deterministic explanation is available for this command yet.")
        lines.append("If an AI backend is configured, a future CAIROS version can delegate richer explanation to it.")

    lines.append("Context:")
    if lowered.startswith("git reset --soft"):
        lines.append("- Commonly used to undo a commit while keeping the changed files staged.")
    elif lowered.startswith("git reset --hard"):
        lines.append("- Use only when you are certain local changes can be discarded.")
    else:
        lines.append("- Interpreted deterministically by CAIROS without an AI call.")
    lines.append(f"Risk: {safety.risk}")
    lines.append("What changes:")
    lines.append("- Depends on the command and its arguments; see meaning and safety notes.")
    lines.append("What stays unchanged:")
    lines.append("- CAIROS does not execute commands in explain mode.")
    lines.append("Safer alternative:")
    lines.append("- Run `cairos check <command>` first, or use `cairos plan ...` for structured tasks.")
    lines.append("Safety notes:")
    for reason in safety.reasons:
        lines.append(f"- {reason}")

    if include_context:
        lines.append("Context:")
        lines.extend([f"- {line}" for line in context_summary().splitlines()])
    return "\n".join(lines)
