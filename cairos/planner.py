"""Request planner orchestration for CAIROS.

``make_plan`` is the main entry used by the CLI.  It first tries deterministic
templates.  Only if no template matches and an AI provider is configured does it
call the AI planner.  Every resulting plan is scanned by the safety layer.
"""

from __future__ import annotations

from .ai import AIPlannerError, plan_with_ai
from .config import load_config
from .models import Plan
from .safety import check_steps
from .templates import plan_from_template


def make_plan(request: str, allow_ai: bool = True) -> Plan:
    """Create a safe plan from a user request."""
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
                    "CAIROS could not solve this with local templates.",
                    "No AI backend is configured.",
                    "Try: cairos config ai use-ollama llama3.1",
                    "Try: cairos config ai use-gemini gemini-2.5-flash",
                    "Try: cairos config ai use-openai gpt-4.1-mini",
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
