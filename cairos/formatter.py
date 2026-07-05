from .models import Plan


def format_plan(plan: Plan) -> str:
    lines = [f"Summary: {plan.summary}", f"Risk: {plan.risk}", "Commands:"]
    if plan.commands:
        for index, command in enumerate(plan.commands, 1):
            lines.append(f"{index}. {command}")
    else:
        lines.append("<none>")
    if plan.notes:
        lines.append("Notes:")
        for note in plan.notes:
            lines.append(f"- {note}")
    return "\n".join(lines)
