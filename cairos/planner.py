from .models import Plan
from .templates import plan_from_template
from .safety import check_commands


def make_plan(request: str) -> Plan:
    plan = plan_from_template(request)
    if plan is None:
        plan = Plan(
            summary="No deterministic template matched this request.",
            commands=[],
            risk="medium",
            notes=["Add a template in cairos/templates.py or later connect an AI planner."],
        )
    safety = check_commands(plan.commands) if plan.commands else None
    if safety and safety.risk != "low":
        plan.risk = safety.risk
        plan.notes.extend(safety.reasons)
    return plan
