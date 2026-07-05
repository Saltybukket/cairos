from dataclasses import dataclass
import re

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

@dataclass
class SafetyResult:
    risk: str
    reasons: list[str]
    blocked: bool = False


def _max_risk(a: str, b: str) -> str:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def check_command(command: str) -> SafetyResult:
    cmd = command.strip()
    lowered = cmd.lower()
    risk = "low"
    reasons: list[str] = []

    critical_patterns = [
        (r"rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/$", "recursive force deletion of root"),
        (r"rm\s+-[^\n]*r[^\n]*f[^\n]*\s+~/?$", "recursive force deletion of home directory"),
        (r"sudo\s+rm\s+-[^\n]*r[^\n]*f", "sudo recursive force deletion"),
        (r"mkfs(\.|\s|$)", "filesystem formatting command"),
        (r"dd\s+.*\bof=/dev/", "raw disk write with dd"),
    ]
    high_patterns = [
        (r"chmod\s+-r\s+777\s+(/|~)", "recursive chmod 777 on broad path"),
        (r"chown\s+-r\s+", "recursive ownership change"),
        (r"curl\s+.*\|\s*(bash|sh)", "downloaded script piped into shell"),
        (r"wget\s+.*\|\s*(bash|sh)", "downloaded script piped into shell"),
        (r"git\s+clean\s+-fdx", "git clean deletes untracked and ignored files"),
    ]
    medium_patterns = [
        (r"find\s+\.\s+.*-delete", "find delete can remove many files"),
        (r"rm\s+-[^\n]*r", "recursive deletion"),
    ]

    for pattern, reason in critical_patterns:
        if re.search(pattern, lowered):
            risk = _max_risk(risk, "critical")
            reasons.append(reason)
    if risk != "critical":
        for pattern, reason in high_patterns:
            if re.search(pattern, lowered):
                risk = _max_risk(risk, "high")
                reasons.append(reason)
    if risk not in {"critical", "high"}:
        for pattern, reason in medium_patterns:
            if re.search(pattern, lowered):
                risk = _max_risk(risk, "medium")
                reasons.append(reason)

    blocked = risk == "critical"
    if not reasons:
        reasons.append("no dangerous pattern detected")
    return SafetyResult(risk=risk, reasons=reasons, blocked=blocked)


def check_commands(commands: list[str]) -> SafetyResult:
    risk = "low"
    reasons: list[str] = []
    blocked = False
    for command in commands:
        result = check_command(command)
        risk = _max_risk(risk, result.risk)
        reasons.extend([f"{command}: {reason}" for reason in result.reasons])
        blocked = blocked or result.blocked
    return SafetyResult(risk=risk, reasons=reasons, blocked=blocked)
