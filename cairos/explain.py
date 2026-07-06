from __future__ import annotations

from .context import context_summary
from .safety import check_command


def explain_command(command: str, include_context: bool = True) -> str:
    lowered = command.strip().lower()
    safety = check_command(command)
    lines = [f"Command: {command}", f"Risk: {safety.risk}", "Meaning:"]

    if lowered.startswith("git reset --soft"):
        lines.append("Moves the current branch pointer, but keeps changes staged/in the index.")
        lines.append("Useful for rewriting the last commit without losing file changes.")
    elif lowered.startswith("git reset --hard"):
        lines.append("Moves the current branch pointer and discards matching working tree changes.")
        lines.append("This can permanently lose uncommitted work.")
    elif lowered.startswith("git fetch"):
        lines.append("Downloads remote branch information without merging it into your current branch.")
    elif lowered.startswith("git merge"):
        lines.append("Combines another branch into the current branch and may create a merge commit.")
    elif lowered.startswith("git rebase"):
        lines.append("Replays commits on top of another base commit. This rewrites local commit history.")
    elif lowered.startswith("git push"):
        lines.append("Uploads local commits to a remote repository branch.")
    elif lowered.startswith("rm"):
        lines.append("Removes files or directories. Recursive or force options increase risk.")
    elif lowered.startswith("find"):
        lines.append("Searches files/directories according to filters. Actions like -delete or -exec rm modify files.")
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
    else:
        lines.append("No deterministic explanation is available for this command yet.")
        lines.append("If an AI backend is configured, a future CAIROS version can delegate richer explanation to it.")

    lines.append("Safety notes:")
    for reason in safety.reasons:
        lines.append(f"- {reason}")

    if include_context:
        lines.append("Context:")
        lines.extend([f"- {line}" for line in context_summary().splitlines()])
    return "\n".join(lines)
