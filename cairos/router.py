"""Lightweight request routing and template confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

from .models import Plan
from .shell_utils import FUZZY_FILLER_PATTERNS, extract_navigation_query, fuzzy_search_terms

RouteName = Literal["template", "ai", "conversation", "no_match"]

STRICT_TEMPLATE_THRESHOLD = 0.80
MEDIUM_TEMPLATE_THRESHOLD = 0.45

BROAD_AI_PHRASES = [
    "setup this repo",
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
    reason: str
    complexity: ComplexityResult
    candidate_source: str = "none"
    confidence: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    ignored_tokens: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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


def score_template_candidate(request: str, plan: Plan | None, complexity: ComplexityResult) -> RouteDecision:
    if plan is None:
        return RouteDecision("no_match", "no deterministic template matched", complexity)
    source = plan.source
    warnings = list(plan.template_warnings)
    confidence = plan.template_confidence if plan.template_confidence is not None else 0.90
    matched_terms = list(plan.matched_terms)
    ignored_tokens: list[str] = []
    words = _words(request)

    if source == "template:conversation":
        return RouteDecision("conversation", "offline conversation template", complexity, source, 1.0)

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
        return RouteDecision("template", "template confidence is high", complexity, source, confidence, matched_terms, ignored_tokens, warnings)
    if confidence >= MEDIUM_TEMPLATE_THRESHOLD:
        return RouteDecision("ai", "template confidence is uncertain", complexity, source, confidence, matched_terms, ignored_tokens, warnings)
    return RouteDecision("no_match", "template confidence is too low", complexity, source, confidence, matched_terms, ignored_tokens, warnings)


def format_route_debug(request: str, decision: RouteDecision) -> str:
    lines = [
        "Route debug",
        f"request: {request}",
        f"complexity: {decision.complexity.level}",
        f"complexity_score: {decision.complexity.score:.2f}",
        f"word_count: {decision.complexity.word_count}",
        f"fuzzy phrases: {', '.join(decision.complexity.fuzzy_phrases) or '<none>'}",
        f"clause markers: {', '.join(decision.complexity.clause_markers) or '<none>'}",
        f"candidate: {decision.candidate_source}",
        f"confidence: {decision.confidence:.2f}",
        f"matched terms: {', '.join(decision.matched_terms) or '<none>'}",
        f"ignored tokens: {', '.join(decision.ignored_tokens) or '<none>'}",
        f"warnings: {', '.join(decision.warnings + decision.complexity.warnings) or '<none>'}",
        f"route: {decision.route}",
        f"reason: {decision.reason}",
    ]
    return "\n".join(lines)
