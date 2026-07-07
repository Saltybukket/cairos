"""Core data models used by CAIROS planners and executors.

The central idea is that CAIROS should not throw raw shell strings around
forever.  It should convert user requests into structured ``Plan`` objects with
clear steps, risk levels, notes and verification checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import shlex

Risk = Literal["low", "medium", "high", "critical"]
StepKind = Literal["command", "mkdir", "write_file", "append_file"]

RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class VerificationStep:
    """A small post-execution check, for example that a file exists."""

    kind: Literal["file_exists", "dir_exists", "command_succeeds", "command_output_equals"]
    target: str
    description: str = ""
    expected: str = ""


@dataclass
class CommandStep:
    """One executable or structured step inside a plan."""

    description: str
    kind: StepKind = "command"
    command: str | None = None
    path: str | None = None
    content: str | None = None
    changes_files: bool = False
    risk: Risk = "low"

    def display(self) -> str:
        """Return a human-readable version for plan output."""
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
            return f"mkdir -p {shlex.quote(self.path or '')}"
        if self.kind in {"write_file", "append_file"}:
            redir = ">>" if self.kind == "append_file" else ">"
            content = shlex.quote(self.content or "")
            path = shlex.quote(self.path or "")
            return f"printf %s {content} {redir} {path}"
        return ""


@dataclass
class Plan:
    """A full CAIROS plan produced by templates or AI."""

    summary: str
    steps: list[CommandStep] = field(default_factory=list)
    risk: Risk = "low"
    notes: list[str] = field(default_factory=list)
    source: str = "template"
    requires_confirmation: bool = True
    confirmation_phrase: str = "yes"
    verification: list[VerificationStep] = field(default_factory=list)
    template_confidence: float | None = None
    template_warnings: list[str] = field(default_factory=list)
    matched_terms: list[str] = field(default_factory=list)

    @property
    def commands(self) -> list[str]:
        """Return only raw shell command steps for compatibility."""
        return [step.command for step in self.steps if step.kind == "command" and step.command]

    def joined(self) -> str:
        """Return a shell-style joined command line for ``cairos expand``."""
        return " && ".join(step.shell_equivalent() for step in self.steps if step.shell_equivalent())

    def has_write_actions(self) -> bool:
        """Return True when any step creates, modifies or deletes files."""
        return any(step.changes_files for step in self.steps)

    def recompute_risk(self) -> None:
        """Raise the plan risk to the highest risk of all contained steps."""
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
    """Result of scanning a command or plan for risky patterns."""

    risk: Risk
    reasons: list[str]
    blocked: bool = False


def max_risk(a: str, b: str) -> Risk:
    """Return the higher of two risk levels."""
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b  # type: ignore[return-value]


def normalize_path(path: str) -> str:
    """Normalize a path string for display/comparison."""
    return str(Path(path))
