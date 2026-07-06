from __future__ import annotations

import re
from .models import CommandStep, SafetyResult, max_risk

CRITICAL_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+-[^\n]*r[^\n]*f[^\n]*(\s+--no-preserve-root)?\s+/$", "recursive force deletion of root"),
    (r"\brm\s+-[^\n]*r[^\n]*f[^\n]*\s+(/\*|/\.\.?)(\s|$)", "recursive force deletion of a root glob"),
    (r"\brm\s+-[^\n]*r[^\n]*f[^\n]*\s+~/?$", "recursive force deletion of home directory"),
    (r"\bsudo\s+rm\s+-[^\n]*r[^\n]*f", "sudo recursive force deletion"),
    (r"\bmkfs(\.|\s|$)", "filesystem formatting command"),
    (r"\bdd\s+.*\bof=/dev/", "raw disk write with dd"),
    (r":\(\)\s*\{\s*:\|:&\s*}\s*;\s*:", "fork bomb pattern"),
    (r">\s*/dev/sd[a-z]\b", "redirecting output to a raw disk device"),
]

HIGH_PATTERNS: list[tuple[str, str]] = [
    (r"\bchmod\s+-r\s+777\s+(/|~)", "recursive chmod 777 on broad path"),
    (r"\bchown\s+-r\s+", "recursive ownership change"),
    (r"\bcurl\s+.*\|\s*(bash|sh)\b", "downloaded script piped into shell"),
    (r"\bwget\s+.*\|\s*(bash|sh)\b", "downloaded script piped into shell"),
    (r"\bgit\s+clean\s+.*-[a-z]*f[a-z]*d[a-z]*x", "git clean deletes untracked and ignored files"),
    (r"\bgit\s+push\s+.*--force", "force push rewrites remote history"),
    (r"\bgit\s+reset\s+--hard", "hard reset discards local changes"),
]

MEDIUM_PATTERNS: list[tuple[str, str]] = [
    (r"\bfind\s+\.\s+.*-delete", "find delete can remove many files"),
    (r"\brm\s+-[^\n]*r", "recursive deletion"),
    (r"\brm\s+[^\n]*\*", "rm with glob can delete multiple files"),
    (r"\bmv\s+[^\n]+\s+(/|~)", "move operation targets a broad path"),
]


def check_command(command: str) -> SafetyResult:
    cmd = command.strip()
    lowered = cmd.lower()
    risk = "low"
    reasons: list[str] = []

    for pattern, reason in CRITICAL_PATTERNS:
        if re.search(pattern, lowered):
            risk = max_risk(risk, "critical")
            reasons.append(reason)

    if risk != "critical":
        for pattern, reason in HIGH_PATTERNS:
            if re.search(pattern, lowered):
                risk = max_risk(risk, "high")
                reasons.append(reason)

    if risk not in {"critical", "high"}:
        for pattern, reason in MEDIUM_PATTERNS:
            if re.search(pattern, lowered):
                risk = max_risk(risk, "medium")
                reasons.append(reason)

    blocked = risk == "critical"
    if not reasons:
        reasons.append("no dangerous pattern detected")
    return SafetyResult(risk=risk, reasons=reasons, blocked=blocked)


def check_steps(steps: list[CommandStep]) -> SafetyResult:
    risk = "low"
    reasons: list[str] = []
    blocked = False

    for step in steps:
        risk = max_risk(risk, step.risk)
        if step.kind == "command" and step.command:
            result = check_command(step.command)
            risk = max_risk(risk, result.risk)
            reasons.extend([f"{step.display()}: {reason}" for reason in result.reasons])
            blocked = blocked or result.blocked
        else:
            reasons.append(f"{step.display()}: structured {step.kind} action")

    if not steps:
        reasons.append("no commands to check")
    return SafetyResult(risk=risk, reasons=reasons, blocked=blocked)


def check_commands(commands: list[str]) -> SafetyResult:
    steps = [CommandStep(description=cmd, command=cmd, kind="command") for cmd in commands]
    return check_steps(steps)
