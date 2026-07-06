"""Preview and diff helpers for CAIROS plans."""

from __future__ import annotations

import difflib
from pathlib import Path

from .models import Plan


def preview_plan(plan: Plan) -> str:
    """Describe files and commands a plan would affect without executing it."""
    lines = [
        f"Preview: {plan.summary}",
        f"Source: {plan.source}",
        f"Risk: {plan.risk}",
        f"Requires confirmation: {'yes' if plan.requires_confirmation else 'no'}",
    ]
    if not plan.steps:
        lines.append("<no steps>")
        return "\n".join(lines)
    for index, step in enumerate(plan.steps, 1):
        if step.path:
            exists = Path(step.path).exists()
            state = "modify existing" if exists else "create new"
            lines.append(f"{index}. {state}: {step.path}")
        else:
            lines.append(f"{index}. command: {step.display()}")
    return "\n".join(lines)


def diff_plan(plan: Plan) -> str:
    """Return unified diffs for file-writing steps where possible."""
    lines = [f"Diff: {plan.summary}"]
    any_diff = False
    for step in plan.steps:
        if step.kind not in {"write_file", "append_file"} or not step.path:
            continue
        any_diff = True
        path = Path(step.path)
        before = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
        after_text = (path.read_text(encoding="utf-8") if path.exists() and step.kind == "append_file" else "") + (step.content or "")
        after = after_text.splitlines(keepends=True)
        lines.extend(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"a/{step.path}",
                tofile=f"b/{step.path}",
                lineterm="",
            )
        )
    if not any_diff:
        lines.append("No file write steps can be diffed.")
    return "\n".join(lines)
