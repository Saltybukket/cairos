from __future__ import annotations

from .ai import AIPlannerError, plan_with_ai
from .config import load_config
from .models import Plan
from .safety import check_steps
from .templates import plan_from_template


def make_plan(request: str, allow_ai: bool = True) -> Plan:
    plan = plan_from_template(request)
    if plan is None:
        if allow_ai and load_config()["ai"].get("provider", "none") != "none":
            try:
                plan = plan_with_ai(request)
            except AIPlannerError as exc:
                return Plan(
                    summary="No deterministic template matched, and the configured AI backend failed.",
                    steps=[],
                    risk="medium",
                    notes=[str(exc)],
                    source="none",
                    requires_confirmation=False,
                )
        else:
            return Plan(
                summary="No deterministic template matched this request.",
                steps=[],
                risk="medium",
                notes=[
                    "No AI backend is configured.",
                    "Configure one with: cairos config ai set-provider ollama",
                    "Or add a deterministic template in cairos/templates.py.",
                ],
                source="none",
                requires_confirmation=False,
            )

    safety = check_steps(plan.steps)
    if safety.risk != "low":
        plan.risk = safety.risk
        plan.notes.extend(safety.reasons)
    if safety.blocked:
        plan.risk = "critical"
        plan.notes.append("Plan contains a critical command and will be blocked.")
    plan.recompute_risk()
    if not plan.has_write_actions() and plan.risk == "low":
        plan.requires_confirmation = False
    return plan
