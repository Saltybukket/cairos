from __future__ import annotations

from .models import Plan


def format_plan(plan: Plan, verbose: bool = True) -> str:
    lines = [
        f"Summary: {plan.summary}",
        f"Source: {plan.source}",
        f"Risk: {plan.risk}",
        f"Requires confirmation: {'yes' if plan.requires_confirmation else 'no'}",
        "Steps:",
    ]
    if plan.steps:
        for index, step in enumerate(plan.steps, 1):
            lines.append(f"{index}. {step.display()}")
            if verbose:
                lines.append(f"   - {step.description}")
                lines.append(f"   - kind={step.kind}, changes_files={'yes' if step.changes_files else 'no'}, risk={step.risk}")
    else:
        lines.append("<none>")
    if plan.verification:
        lines.append("Verification:")
        for item in plan.verification:
            desc = f" - {item.description}" if item.description else ""
            lines.append(f"- {item.kind}: {item.target}{desc}")
    if plan.notes:
        lines.append("Notes:")
        for note in plan.notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


def format_short_summary(title: str, lines: list[str]) -> str:
    return "\n".join([title, *[f"- {line}" for line in lines]])
