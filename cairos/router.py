"""Lightweight request routing and template confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Literal

from .models import Plan
from .shell_utils import FUZZY_FILLER_PATTERNS, extract_navigation_query, fuzzy_search_terms

ROUTE_TEMPLATE = "template"
ROUTE_AI = "ai"
ROUTE_CONVERSATION = "conversation"
ROUTE_SAFETY_CHECK = "safety_check"
ROUTE_NO_MATCH = "no_match"

RouteName = Literal["template", "ai", "conversation", "safety_check", "no_match"]

STRICT_TEMPLATE_THRESHOLD = 0.80
MEDIUM_TEMPLATE_THRESHOLD = 0.45

BROAD_AI_PHRASES = [
    "setup this repo",
    "setup this whole repo",
    "clean release",
    "ready for release",
    "fix anything",
    "fix all",
    "make this repo",
    "make project production ready",
    "clean everything",
    "move the folder that looks",
    "tell me what to fix",
]

CLAUSE_MARKERS = [" and then ", " but ", " except ", " - ", ";", " && "]
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+/",
    r"\brm\s+-rf\s+\*",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+push\s+-f\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-fdx\b",
    r"\bdd\s+if=.*\bof=/dev/",
    r"\bmkfs\.",
    r"\bchmod\s+-R\s+777\b",
    r"\bchown\s+-R\b",
    r"\bcurl\b.*\|\s*(?:sh|bash)\b",
    r"\bwget\b.*\|\s*(?:sh|bash)\b",
]
CONVERSATION_INPUTS = {"hello", "hi", "hey", "how are you", "thanks", "thank you", "danke"}
SIMPLE_TEMPLATE_PATTERNS = [
    r"^(?:cairos\s+)?(?:please\s+|pls\s+)?(?:configure|use)\s+openrouter\s+free\b",
    r"^(?:cairos\s+)?(?:backup\s+config|config\s+backup|update|upgrade|quicksetup|setup)$",
    r"^(?:cairos\s+)?(?:show\s+)?(?:config\s+path|install-info|doctor|history|templates)\b",
    r"^(?:cairos\s+)?(?:disable|enable|configure|use)\s+ai\b",
    r"^(?:cairos\s+)?(?:list|show)\s+(?:env|environment)\s+variables\b",
    r"^(?:cairos\s+)?(?:git\s+status\s+summary|check\s+if\s+repo\s+is\s+ready\s+to\s+(?:commit|push))\b",
    r"^(?:cairos\s+)?(?:pip|npm|cargo)\s+(?:install|test|build)\b",
    r"\b(?:create|make|mkdir|erstelle|mache)\s+(?:a\s+)?(?:folder|directory|ordner)\s+[A-Za-z0-9_.-]+$",
    r"\b(?:mach|macke|erstell)\s+(?:dir|ordner|folder)\s+[A-Za-z0-9_.-]+$",
    r"\b(?:create|make|erstelle)\s+(?:a\s+)?file\s+[A-Za-z0-9_./-]+$",
    r"\b(?:erstell|erstelle|make|create)\s+(?:a\s+)?(?:file|datei)\s+[A-Za-z0-9_./-]+$",
    r"\bsay\s+\w+",
    r"\becho\s+.+",
    r"\blist\s+wsl\s+distros",
    r"\bshow\s+disk\s+usage",
    r"\bcreate\s+python\s+project\s+[A-Za-z0-9_-]+\b",
    r"\bcreate\s+cpp\s+mini\s+project\s+[A-Za-z0-9_-]+\b",
]
INSTRUCTION_TERMS = {"current", "working", "shell", "parent", "change", "cahnge", "directory", "folder", "named", "called", "something", "like", "that", "-"}
SIMPLE_ONE_TARGET_SOURCES = {
    "template:folder",
    "template:readme",
    "template:gitignore",
    "template:license",
    "template:editorconfig",
}


@dataclass
class ComplexityResult:
    level: Literal["simple", "medium", "complex"]
    score: float
    word_count: int
    fuzzy_phrases: list[str] = field(default_factory=list)
    clause_markers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RouteDecision:
    route: RouteName
    confidence: float = 0.0
    reason: str = ""
    complexity_score: float = 0.0
    template_allowed: bool = False
    debug: dict[str, object] = field(default_factory=dict)
    complexity: ComplexityResult | None = None
    candidate_source: str = "none"
    matched_terms: list[str] = field(default_factory=list)
    ignored_tokens: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _decision(
    route: RouteName,
    reason: str,
    complexity: ComplexityResult,
    *,
    confidence: float = 0.0,
    template_allowed: bool = False,
    candidate_source: str = "none",
    matched_terms: list[str] | None = None,
    ignored_tokens: list[str] | None = None,
    warnings: list[str] | None = None,
    debug: dict[str, object] | None = None,
) -> RouteDecision:
    combined_debug: dict[str, object] = {
        "complexity": complexity.level,
        "word_count": complexity.word_count,
        "fuzzy_phrases": list(complexity.fuzzy_phrases),
        "clause_markers": list(complexity.clause_markers),
        "warnings": list(complexity.warnings),
    }
    if debug:
        combined_debug.update(debug)
    return RouteDecision(
        route=route,
        confidence=confidence,
        reason=reason,
        complexity_score=complexity.score,
        template_allowed=template_allowed,
        debug=combined_debug,
        complexity=complexity,
        candidate_source=candidate_source,
        matched_terms=matched_terms or [],
        ignored_tokens=ignored_tokens or [],
        warnings=warnings or [],
    )


def _words(request: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_.-]+", request.lower())


def classify_request_complexity(request: str) -> ComplexityResult:
    text = request.lower()
    words = _words(request)
    fuzzy = []
    for pattern in FUZZY_FILLER_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            fuzzy.append(match.group(0))
    clauses = [marker.strip() for marker in CLAUSE_MARKERS if marker in text]
    warnings: list[str] = []
    score = 0.0
    if len(words) > 10:
        score += 0.25
        warnings.append("long request")
    if len(words) > 18:
        score += 0.20
    if fuzzy:
        score += 0.30
        warnings.append("fuzzy language")
    if clauses:
        score += 0.25
        warnings.append("multiple clauses")
    if any(phrase in text for phrase in BROAD_AI_PHRASES):
        score += 0.45
        warnings.append("broad project-management request")
    if " with " in text and any(word in words for word in ["nice", "everything", "anything", "fix"]):
        score += 0.25
        warnings.append("open-ended modifier")
    level: Literal["simple", "medium", "complex"] = "simple"
    if score >= 0.65:
        level = "complex"
    elif score >= 0.30:
        level = "medium"
    return ComplexityResult(level=level, score=min(score, 1.0), word_count=len(words), fuzzy_phrases=fuzzy, clause_markers=clauses, warnings=warnings)


def _heuristic_route_request(request: str) -> RouteDecision:
    text = request.strip().lower().rstrip("!?.,")
    complexity = classify_request_complexity(request)
    words = _words(request)
    if not text:
        return _decision(ROUTE_NO_MATCH, "empty request", complexity, confidence=1.0)
    if text in CONVERSATION_INPUTS:
        return _decision(ROUTE_CONVERSATION, "common conversational input", complexity, confidence=0.98)
    if any(re.search(pattern, text) for pattern in DANGEROUS_PATTERNS):
        return _decision(ROUTE_SAFETY_CHECK, "dangerous shell command pattern", complexity, confidence=0.95)
    if any(phrase in text for phrase in BROAD_AI_PHRASES):
        return _decision(ROUTE_AI, "broad or project-management request", complexity, confidence=0.82)
    if complexity.level == "complex":
        return _decision(ROUTE_AI, "complex or multi-clause request", complexity, confidence=0.74)
    if any(re.search(pattern, text) for pattern in SIMPLE_TEMPLATE_PATTERNS):
        return _decision(ROUTE_TEMPLATE, "simple template-compatible request", complexity, confidence=0.88, template_allowed=True)
    if {"go", "cd", "change", "find"}.intersection(words) and {"directory", "folder", "dir"}.intersection(words):
        terms = fuzzy_search_terms(extract_navigation_query(request))
        if terms and not set(t.lower() for t in terms).intersection(INSTRUCTION_TERMS):
            return _decision(ROUTE_TEMPLATE, "directory navigation with valid target terms", complexity, confidence=0.86, template_allowed=True, matched_terms=terms)
        return _decision(ROUTE_NO_MATCH, "directory navigation target was not reliable", complexity, confidence=0.70, matched_terms=terms)
    if complexity.level == "medium":
        return _decision(ROUTE_AI, "medium complexity request", complexity, confidence=0.62)
    return _decision(ROUTE_NO_MATCH, "no clear route matched", complexity, confidence=0.55)


def _model_paths() -> list[Path]:
    package_root = Path(__file__).resolve().parents[1]
    return [
        Path.cwd() / "data" / "router_model.joblib",
        package_root / "data" / "router_model.joblib",
        package_root / "cairos" / "data" / "router_model.joblib",
    ]


def _ml_route_request(request: str) -> RouteDecision | None:
    try:
        import joblib  # type: ignore[import-not-found]
    except Exception:
        return None
    model_path = next((path for path in _model_paths() if path.exists()), None)
    if model_path is None:
        return None
    try:
        model = joblib.load(model_path)
        label = str(model.predict([request])[0])
        confidence = 0.0
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba([request])[0]
            confidence = float(max(probabilities))
        complexity = classify_request_complexity(request)
        if label not in {ROUTE_TEMPLATE, ROUTE_AI, ROUTE_CONVERSATION, ROUTE_SAFETY_CHECK, ROUTE_NO_MATCH}:
            label = ROUTE_NO_MATCH
        return _decision(
            label,  # type: ignore[arg-type]
            "ml router prediction",
            complexity,
            confidence=confidence,
            template_allowed=label == ROUTE_TEMPLATE,
            debug={"router_type": "ml", "model_path": str(model_path)},
        )
    except Exception:
        return None


def route_request(request: str, *, allow_ml: bool = True, router: str = "auto") -> RouteDecision:
    """Route a request with optional ML and safe heuristic fallback."""
    if allow_ml and router in {"auto", "ml"}:
        decision = _ml_route_request(request)
        if decision is not None:
            return decision
        if router == "ml":
            heuristic = _heuristic_route_request(request)
            heuristic.reason = "ml router unavailable; " + heuristic.reason
            heuristic.debug["router_type"] = "heuristic-fallback"
            return heuristic
    decision = _heuristic_route_request(request)
    decision.debug["router_type"] = "heuristic"
    return decision


def score_template_candidate(request: str, plan: Plan | None, complexity: ComplexityResult) -> RouteDecision:
    if plan is None:
        return _decision(ROUTE_NO_MATCH, "no deterministic template matched", complexity)
    source = plan.source
    warnings = list(plan.template_warnings)
    confidence = plan.template_confidence if plan.template_confidence is not None else 0.90
    matched_terms = list(plan.matched_terms)
    ignored_tokens: list[str] = []
    words = _words(request)

    if source == "template:conversation":
        return _decision(ROUTE_CONVERSATION, "offline conversation template", complexity, confidence=1.0, candidate_source=source)

    if complexity.level == "complex":
        confidence -= 0.25
    elif complexity.level == "medium":
        confidence -= 0.10
    if complexity.fuzzy_phrases:
        confidence -= 0.10
    if complexity.clause_markers and source not in {"template:cd-guidance"}:
        confidence -= 0.15
    if "open-ended modifier" in complexity.warnings:
        confidence -= 0.20

    if source == "template:cd-guidance":
        query = extract_navigation_query(request)
        matched_terms = fuzzy_search_terms(query)
        ignored_tokens = sorted(set(words).intersection(INSTRUCTION_TERMS) - set(term.lower() for term in matched_terms))
        if not matched_terms:
            confidence = min(confidence, 0.30)
            warnings.append("no navigation target terms")
        if any(term in INSTRUCTION_TERMS or term == "something" or term == "-" for term in (t.lower() for t in matched_terms)):
            confidence = min(confidence, 0.30)
            warnings.append("navigation target includes instruction/filler terms")
        if len(matched_terms) > 5:
            confidence = min(confidence, 0.45)
            warnings.append("too many navigation target terms")
        if len(matched_terms) in {1, 2, 3} and not warnings:
            confidence = max(confidence, 0.86)
    elif any(phrase in request.lower() for phrase in BROAD_AI_PHRASES):
        confidence = min(confidence, 0.35)
        warnings.append("broad request should use AI or clarification")

    if source in SIMPLE_ONE_TARGET_SOURCES:
        target_words = {"folder", "directory", "dir", "file", "readme", "main.py", "class", "function", "project"}
        target_count = sum(1 for word in target_words if word in request.lower())
        if " with " in request.lower() and target_count >= 2:
            confidence = min(confidence, 0.40)
            warnings.append("simple one-target template cannot satisfy compound request")

    confidence = max(0.0, min(confidence, 1.0))
    if confidence >= STRICT_TEMPLATE_THRESHOLD:
        return _decision(ROUTE_TEMPLATE, "template confidence is high", complexity, confidence=confidence, template_allowed=True, candidate_source=source, matched_terms=matched_terms, ignored_tokens=ignored_tokens, warnings=warnings)
    if confidence >= MEDIUM_TEMPLATE_THRESHOLD:
        return _decision(ROUTE_AI, "template confidence is uncertain", complexity, confidence=confidence, candidate_source=source, matched_terms=matched_terms, ignored_tokens=ignored_tokens, warnings=warnings)
    return _decision(ROUTE_NO_MATCH, "template confidence is too low", complexity, confidence=confidence, candidate_source=source, matched_terms=matched_terms, ignored_tokens=ignored_tokens, warnings=warnings)


def format_route_debug(request: str, decision: RouteDecision) -> str:
    lines = [
        "Route debug",
        f"request: {request}",
        f"router type: {decision.debug.get('router_type', 'heuristic')}",
        f"complexity: {decision.complexity.level if decision.complexity else decision.debug.get('complexity', '<unknown>')}",
        f"complexity_score: {decision.complexity_score:.2f}",
        f"word_count: {decision.complexity.word_count if decision.complexity else decision.debug.get('word_count', '<unknown>')}",
        f"fuzzy phrases: {', '.join(decision.complexity.fuzzy_phrases if decision.complexity else decision.debug.get('fuzzy_phrases', [])) or '<none>'}",
        f"clause markers: {', '.join(decision.complexity.clause_markers if decision.complexity else decision.debug.get('clause_markers', [])) or '<none>'}",
        f"candidate: {decision.candidate_source}",
        f"confidence: {decision.confidence:.2f}",
        f"matched terms: {', '.join(decision.matched_terms) or '<none>'}",
        f"ignored tokens: {', '.join(decision.ignored_tokens) or '<none>'}",
        f"warnings: {', '.join(decision.warnings + (decision.complexity.warnings if decision.complexity else [])) or '<none>'}",
        f"route: {decision.route}",
        f"reason: {decision.reason}",
        f"template_allowed: {'yes' if decision.template_allowed else 'no'}",
    ]
    return "\n".join(lines)
