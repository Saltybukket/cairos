from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Risk = Literal["low", "medium", "high", "critical"]
StepKind = Literal["command", "mkdir", "write_file", "append_file"]

RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class VerificationStep:
    kind: Literal["file_exists", "dir_exists", "command_succeeds"]
    target: str
    description: str = ""


@dataclass
class CommandStep:
    description: str
    kind: StepKind = "command"
    command: str | None = None
    path: str | None = None
    content: str | None = None
    changes_files: bool = False
    risk: Risk = "low"

    def display(self) -> str:
        if self.kind == "command":
            return self.command or ""
        if self.kind == "mkdir":
            return f"mkdir -p {self.path}"
        if self.kind == "write_file":
            return f"write file {self.path}"
        if self.kind == "append_file":
            return f"append file {self.path}"
        return self.description

    def shell_equivalent(self) -> str:
        """Best-effort one-line shell equivalent for expand mode."""
        if self.kind == "command":
            return self.command or ""
        if self.kind == "mkdir":
            return f"mkdir -p {self.path}"
        if self.kind in {"write_file", "append_file"}:
            redir = ">>" if self.kind == "append_file" else ">"
            escaped = (self.content or "").replace("'", "'\"'\"'")
            return f"printf '%s' '{escaped}' {redir} {self.path}"
        return ""


@dataclass
class Plan:
    summary: str
    steps: list[CommandStep] = field(default_factory=list)
    risk: Risk = "low"
    notes: list[str] = field(default_factory=list)
    source: str = "template"
    requires_confirmation: bool = True
    confirmation_phrase: str = "yes"
    verification: list[VerificationStep] = field(default_factory=list)

    @property
    def commands(self) -> list[str]:
        return [step.command for step in self.steps if step.kind == "command" and step.command]

    def joined(self) -> str:
        return " && ".join(step.shell_equivalent() for step in self.steps if step.shell_equivalent())

    def has_write_actions(self) -> bool:
        return any(step.changes_files for step in self.steps)

    def recompute_risk(self) -> None:
        risk = self.risk
        for step in self.steps:
            if RISK_ORDER[step.risk] > RISK_ORDER[risk]:
                risk = step.risk
        self.risk = risk  # type: ignore[assignment]
        if self.risk == "high" and self.confirmation_phrase == "yes":
            self.confirmation_phrase = "execute high risk plan"
        if self.risk == "critical":
            self.confirmation_phrase = "blocked"


@dataclass
class SafetyResult:
    risk: Risk
    reasons: list[str]
    blocked: bool = False


def max_risk(a: str, b: str) -> Risk:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b  # type: ignore[return-value]


def normalize_path(path: str) -> str:
    return str(Path(path))
