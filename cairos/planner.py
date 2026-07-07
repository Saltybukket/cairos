"""Request planner orchestration for CAIROS.

``make_plan`` is the main entry used by the CLI.  It first tries deterministic
templates.  Only if no template matches and an AI provider is configured does it
call the AI planner.  Every resulting plan is scanned by the safety layer.
"""

from __future__ import annotations

from .ai import AIPlannerError, plan_with_ai_fallback

from .config import load_config
from .models import Plan
from .router import ROUTE_AI, ROUTE_CONVERSATION, ROUTE_NO_MATCH, ROUTE_SAFETY_CHECK, RouteDecision, classify_request_complexity, route_request, score_template_candidate
from .safety import check_steps
from .templates import plan_from_template


def _ai_is_configured_and_available(config: dict) -> bool:
    ai = config["ai"]
    provider = ai.get("provider", "none")
    return provider != "none" or bool(config.get("ai_profiles"))


def _no_reliable_template_plan(request: str, decision: RouteDecision, ai_configured: bool) -> Plan:
    notes = [
        "The request looks complex or ambiguous.",
        "CAIROS avoided using a low-confidence deterministic template.",
    ]
    if decision.candidate_source == "template:cd-guidance" and decision.matched_terms:
        query = " ".join(decision.matched_terms)
        notes.append(f"Try: cairos find-dir \"{query}\"")
    if ai_configured:
        notes.append("An AI backend is configured but is not available in this shell. Check `cairos config ai status`.")
    else:
        notes.append("Configure AI fallback, or simplify the request.")
    return Plan(
        summary="No reliable deterministic template matched.",
        steps=[],
        risk="low",
        notes=notes,
        source="none",
        requires_confirmation=False,
    )


def _fallback_or_no_match(request: str, allow_ai: bool, decision: RouteDecision, config: dict) -> Plan:
    if allow_ai and _ai_is_configured_and_available(config):
        try:
            return plan_with_ai_fallback(request)
        except AIPlannerError as exc:
            return Plan(
                summary="No reliable deterministic template matched, and the configured AI backend failed.",
                steps=[],
                risk="medium",
                notes=[str(exc)],
                source="none",
                requires_confirmation=False,
            )
    return _no_reliable_template_plan(request, decision, ai_configured=config["ai"].get("provider", "none") != "none")


def make_plan(request: str, allow_ai: bool = True) -> Plan:
    """Create a safe plan from a user request."""
    config = load_config()
    behavior = config.get("behavior", {})
    pre_route = route_request(
        request,
        allow_ml=bool(behavior.get("ml_router_enabled", False)),
        router=str(behavior.get("router", "auto")),
    )
    if pre_route.route == ROUTE_CONVERSATION:
        plan = plan_from_template(request)
        if plan is not None:
            plan.template_confidence = pre_route.confidence
            return plan
    if pre_route.route == ROUTE_NO_MATCH and pre_route.confidence >= 0.80:
        return _no_reliable_template_plan(request, pre_route, ai_configured=config["ai"].get("provider", "none") != "none")
    if pre_route.route == ROUTE_AI and pre_route.confidence >= 0.80:
        return _fallback_or_no_match(request, allow_ai, pre_route, config)
    # Safety checks are handled explicitly by `cairos check`; direct planning still
    # goes through templates/AI so it can show a normal CAIROS plan.
    _ = ROUTE_SAFETY_CHECK
    plan = plan_from_template(request)
    decision = score_template_candidate(request, plan, classify_request_complexity(request))
    ai_on_uncertain = bool(behavior.get("ai_on_uncertain_template", True))

    if plan is None:
        if allow_ai and _ai_is_configured_and_available(config):
            try:
                plan = plan_with_ai_fallback(request)
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
                    "Or inspect templates: cairos templates",
                ],
                source="none",
                requires_confirmation=False,
            )

    if decision.route == "ai" and ai_on_uncertain:
        plan = _fallback_or_no_match(request, allow_ai, decision, config)
    elif decision.route == "no_match":
        plan = _fallback_or_no_match(request, allow_ai, decision, config)
    elif plan is not None:
        plan.template_confidence = decision.confidence
        plan.template_warnings.extend(decision.warnings)
        plan.matched_terms = decision.matched_terms or plan.matched_terms

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
