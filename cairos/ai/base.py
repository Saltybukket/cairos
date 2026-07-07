"""AI backend adapter layer for CAIROS.

The deterministic template system should solve common tasks first.  This module
is only used as a fallback when templates cannot understand the request and an
AI backend has been configured.

Supported providers:
- ``ollama``: local HTTP API at http://localhost:11434
- ``openai`` / ``openai-compatible``: chat-completions compatible API
- ``gemini``: Google Gemini generateContent API
- ``custom-command``: local command reading JSON from stdin and printing plan JSON
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from ..config import activate_ai_profile, env_var_setup_hint, load_config
from ..context import collect_context
from ..models import CommandStep, Plan, VerificationStep
from ..rules import load_rules


@dataclass
class AiFailure:
    profile: str
    provider: str
    model: str
    endpoint: str | None
    status_code: int | None
    category: str
    message: str
    recoverable: bool


class AIPlannerError(RuntimeError):
    """Raised when an AI backend is missing, unreachable or returns invalid JSON."""

    def __init__(self, message: str, failure: AiFailure | None = None):
        super().__init__(message)
        self.failure = failure


def _system_prompt() -> str:
    """Return the strict JSON-only planner prompt used for all backends."""
    return (
        "You are CAIROS, a safe shell planning assistant. "
        "Return ONLY valid JSON. Do not include markdown. "
        "Prefer structured steps over raw shell commands. "
        "Never include critical destructive commands. "
        "Ask CAIROS to require confirmation for anything that changes files. "
        "Schema: {summary: string, risk: low|medium|high|critical, "
        "steps: [{kind: command|mkdir|write_file|append_file, description: string, command?: string, path?: string, content?: string, changes_files?: boolean, risk?: low|medium|high|critical}], "
        "notes: [string], verification: [{kind: file_exists|dir_exists|command_succeeds, target: string, description?: string}]}"
    )


def _build_payload(request: str) -> dict[str, Any]:
    """Build the compact request/context payload sent to AI."""
    cfg = load_config()
    max_files = int(cfg.get("behavior", {}).get("max_context_files", 80))
    return {
        "system": _system_prompt(),
        "request": request,
        "context": collect_context(max_files=max_files),
        "rules": load_rules(),
    }


def _missing_key_message(key_env: str) -> str:
    return (
        f"Missing API key environment variable: {key_env}\n\n"
        f"{env_var_setup_hint(key_env)}\n\n"
        "Then test:\n"
        "  cairos config ai test\n\n"
        "Or switch to another saved AI profile:\n"
        "  cairos config ai profiles\n"
        "  cairos config ai switch\n\n"
        "For persistent setup, add it to your shell profile or a sourced secrets file."
    )


def _error_body_message(body: str) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body.strip()[:500]
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or error)[:500]
        if isinstance(error, str):
            return error[:500]
        if "message" in data:
            return str(data["message"])[:500]
    return str(data)[:500]


def _provider_context(config: dict[str, Any]) -> list[str]:
    ai = config["ai"]
    return [
        f"provider: {ai.get('provider', 'none')}",
        f"model: {ai.get('model') or '<not set>'}",
        f"endpoint: {ai.get('endpoint') or '<not set>'}",
        f"api_key_env: {ai.get('api_key_env') or 'none'}",
        f"active_profile: {config.get('active_ai_profile') or '<none>'}",
    ]


def _failure_context(config: dict[str, Any]) -> tuple[str, str, str, str | None]:
    ai = config.get("ai", {})
    return (
        str(config.get("active_ai_profile") or "<current>"),
        str(ai.get("provider", "none")),
        str(ai.get("model") or ""),
        str(ai.get("endpoint") or "") or None,
    )


def _http_category(status_code: int) -> tuple[str, bool]:
    if status_code == 402:
        return "insufficient_credits", True
    if status_code == 429:
        return "rate_limit_quota", True
    if status_code in {502, 503, 504}:
        return "temporary_provider", True
    if status_code in {401, 403}:
        return "auth", True
    if status_code == 404:
        return "model_unavailable", True
    if 500 <= status_code < 600:
        return "temporary_provider", True
    return "provider_error", False


def _make_failure(config: dict[str, Any], category: str, message: str, recoverable: bool, status_code: int | None = None) -> AiFailure:
    profile, provider, model, endpoint = _failure_context(config)
    return AiFailure(
        profile=profile,
        provider=provider,
        model=model,
        endpoint=endpoint,
        status_code=status_code,
        category=category,
        message=message,
        recoverable=recoverable,
    )


def _failure_from_http(exc: urllib.error.HTTPError, config: dict[str, Any], message: str) -> AiFailure:
    category, recoverable = _http_category(int(exc.code))
    return _make_failure(config, category, message, recoverable, status_code=int(exc.code))


def _format_http_error(prefix: str, exc: urllib.error.HTTPError, config: dict[str, Any], body: str = "") -> str:
    ai = config["ai"]
    endpoint = str(ai.get("endpoint") or "")
    message = _error_body_message(body)
    lines = [f"{prefix} failed with HTTP {exc.code}."]
    if exc.code == 401:
        lines.append("Key missing, invalid, expired, restricted, or not allowed for this model/endpoint.")
        lines.append("Check that the environment variable is visible in this shell, regenerate the key if needed, and verify account/org/project permissions.")
    elif exc.code == 402:
        lines.append("Payment required / insufficient credits.")
        if "openrouter.ai" in endpoint:
            lines.append("This usually means your OpenRouter account has no credits for this paid model.")
            lines.append("Try OpenRouter free or a model ending in :free, or add credits in OpenRouter.")
            lines.append("Suggested commands:")
            lines.append("  cairos config ai use-openrouter-free")
            lines.append("  cairos config ai test")
    elif exc.code == 403:
        lines.append("Forbidden or restricted. The key may not be allowed for this model, endpoint, account, org, or project.")
    elif exc.code == 404:
        lines.append("Model or endpoint not found. Check the model slug and base endpoint.")
        if ai.get("provider") == "gemini":
            lines.append("Try: cairos config ai list-models")
        elif "openrouter.ai" in endpoint:
            lines.append("Check OpenRouter's current model list or try: cairos config ai use-openrouter-free")
    elif exc.code == 429:
        lines.append("Rate limit, quota, or usage limit reached.")
        lines.append("Possible causes: too many requests, free-tier rate limit, quota exhausted, billing not enabled, credits exhausted, or provider throttling.")
        lines.append("Try again later, use a cheaper/free model, check provider usage/billing, or switch profiles.")
    else:
        lines.append("Provider returned an HTTP error. Check endpoint, model, key permissions and provider status.")
    if message:
        lines.append(f"provider message: {message}")
    lines.extend(_provider_context(config))
    return "\n".join(lines)


def _format_network_error(prefix: str, exc: BaseException, config: dict[str, Any]) -> str:
    lines = [
        f"{prefix} network error: {exc}",
        "Check connection, proxy, DNS, TLS certificates, endpoint URL, and provider status.",
    ]
    lines.extend(_provider_context(config))
    return "\n".join(lines)


def _extract_json_object(raw: str) -> str:
    """Extract a JSON object even if a model accidentally adds tiny prose."""
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise AIPlannerError("AI response did not contain a JSON object")
    return match.group(0)


def _normalize_gemini_model(model: str) -> str:
    """Accept ``gemini-x`` or ``models/gemini-x`` and return ``gemini-x``."""
    return model.removeprefix("models/").strip() or "gemini-2.5-flash"


def _parse_plan(raw: str) -> Plan:
    """Parse and validate AI-produced JSON into a ``Plan``."""
    try:
        data = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise AIPlannerError(f"AI returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise AIPlannerError("AI response must be a JSON object")

    steps: list[CommandStep] = []
    for item in data.get("steps", []):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind", "command")
        if kind not in {"command", "mkdir", "write_file", "append_file"}:
            raise AIPlannerError(f"AI returned unsupported step kind: {kind}")
        steps.append(
            CommandStep(
                kind=kind,
                description=str(item.get("description") or item.get("command") or item.get("path") or "AI step"),
                command=item.get("command"),
                path=item.get("path"),
                content=item.get("content"),
                changes_files=bool(item.get("changes_files", kind != "command")),
                risk=item.get("risk", "medium") if item.get("risk") in {"low", "medium", "high", "critical"} else "medium",
            )
        )

    verification = [
        VerificationStep(kind=v.get("kind", "file_exists"), target=str(v.get("target", "")), description=str(v.get("description", "")), expected=str(v.get("expected", "")))
        for v in data.get("verification", [])
        if isinstance(v, dict) and v.get("target")
    ]

    plan = Plan(
        summary=str(data.get("summary", "AI generated plan.")),
        steps=steps,
        risk=data.get("risk", "medium"),
        notes=[str(n) for n in data.get("notes", [])],
        source="ai",
        verification=verification,
        requires_confirmation=True,
    )
    plan.recompute_risk()
    return plan


def _ollama_plan(request: str, config: dict[str, Any]) -> Plan:
    """Call a local Ollama model and parse the returned plan."""
    ai = config["ai"]
    endpoint = ai.get("endpoint") or "http://localhost:11434"
    model = ai.get("model") or "llama3.1"
    timeout = int(ai.get("timeout_seconds", 60))
    payload = _build_payload(request)
    prompt = json.dumps(payload, indent=2)
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        message = f"Ollama backend failed: {exc}"
        category = "network" if isinstance(exc, (urllib.error.URLError, TimeoutError)) else "provider_error"
        raise AIPlannerError(message, failure=_make_failure(config, category, message, category == "network")) from exc
    return _parse_plan(str(data.get("response", "")))


def _openai_compatible_plan(request: str, config: dict[str, Any]) -> Plan:
    """Call an OpenAI-compatible chat completions API."""
    ai = config["ai"]
    endpoint = ai.get("endpoint") or "https://api.openai.com/v1"
    model = ai.get("model") or "gpt-4.1-mini"
    key_env = ai.get("api_key_env") or "OPENAI_API_KEY"
    timeout = int(ai.get("timeout_seconds", 60))
    api_key = os.environ.get(key_env)
    if not api_key:
        message = _missing_key_message(key_env)
        raise AIPlannerError(message, failure=_make_failure(config, "missing_key", f"missing {key_env}", True))
    payload = _build_payload(request)
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": payload["system"]},
                {"role": "user", "content": json.dumps({"request": request, "context": payload["context"], "rules": payload["rules"]})},
            ],
            "temperature": 0.1,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = _format_http_error("OpenAI-compatible backend", exc, config, body)
        raise AIPlannerError(message, failure=_failure_from_http(exc, config, message)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        message = _format_network_error("OpenAI-compatible backend", exc, config)
        raise AIPlannerError(message, failure=_make_failure(config, "network", message, True)) from exc
    except json.JSONDecodeError as exc:
        raise AIPlannerError(f"OpenAI-compatible backend failed: {exc}") from exc
    content = data["choices"][0]["message"]["content"]
    return _parse_plan(content)


def _gemini_plan(request: str, config: dict[str, Any]) -> Plan:
    """Call the Gemini generateContent API and parse the returned plan."""
    ai = config["ai"]
    endpoint = ai.get("endpoint") or "https://generativelanguage.googleapis.com/v1beta"
    model = _normalize_gemini_model(ai.get("model") or "gemini-2.5-flash")
    key_env = ai.get("api_key_env") or "GEMINI_API_KEY"
    timeout = int(ai.get("timeout_seconds", 60))
    api_key = os.environ.get(key_env)
    if not api_key:
        message = _missing_key_message(key_env)
        raise AIPlannerError(message, failure=_make_failure(config, "missing_key", f"missing {key_env}", True))
    payload = _build_payload(request)
    prompt = payload["system"] + "\n\n" + json.dumps({"request": request, "context": payload["context"], "rules": payload["rules"]})
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + f"/models/{model}:generateContent?key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = _format_http_error("Gemini backend", exc, config, body)
        raise AIPlannerError(message, failure=_failure_from_http(exc, config, message)) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        message = _format_network_error("Gemini backend", exc, config)
        raise AIPlannerError(message, failure=_make_failure(config, "network", message, True)) from exc
    except json.JSONDecodeError as exc:
        raise AIPlannerError(f"Gemini backend failed: {exc}") from exc
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_plan(text)


def _custom_command_plan(request: str, config: dict[str, Any]) -> Plan:
    """Call a user-provided local command for planning."""
    command = config["ai"].get("custom_command")
    timeout = int(config["ai"].get("timeout_seconds", 60))
    if not command:
        message = "custom_command is not configured"
        raise AIPlannerError(message, failure=_make_failure(config, "invalid_config", message, False))
    payload = json.dumps(_build_payload(request))
    proc = subprocess.run(command, input=payload, text=True, shell=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        message = f"custom AI command failed: {proc.stderr.strip()}"
        raise AIPlannerError(message, failure=_make_failure(config, "custom_command", message, False))
    return _parse_plan(proc.stdout)


def _plan_with_config(request: str, config: dict[str, Any]) -> Plan:
    provider = config["ai"].get("provider", "none")
    if provider == "none":
        message = "No AI backend configured"
        raise AIPlannerError(message, failure=_make_failure(config, "invalid_config", message, False))
    if provider == "ollama":
        return _ollama_plan(request, config)
    if provider in {"openai", "openai-compatible"}:
        return _openai_compatible_plan(request, config)
    if provider == "gemini":
        return _gemini_plan(request, config)
    if provider == "custom-command":
        return _custom_command_plan(request, config)
    message = f"Unsupported AI provider: {provider}"
    raise AIPlannerError(message, failure=_make_failure(config, "invalid_config", message, False))


def plan_with_ai(request: str) -> Plan:
    """Plan a request with the configured AI provider only."""
    return _plan_with_config(request, load_config())


def _fallback_profile_names(config: dict[str, Any]) -> list[str]:
    profiles = config.get("ai_profiles", {})
    active = str(config.get("active_ai_profile") or "")
    explicit = [str(name) for name in config.get("ai", {}).get("fallback_order", []) if str(name) in profiles]

    def weight(name: str) -> tuple[int, str]:
        lowered = name.lower()
        if "openrouter-free" in lowered or lowered.endswith(":free"):
            return (0, name)
        if "gemini-flash" in lowered or "gemini" in lowered:
            return (1, name)
        if "groq" in lowered:
            return (2, name)
        if "ollama" in lowered or "local" in lowered:
            return (3, name)
        if "mini" in lowered:
            return (4, name)
        return (5, name)

    names: list[str] = []
    for name in [active, *explicit, *sorted(profiles, key=weight)]:
        if name and name in profiles and name not in names:
            names.append(name)
    return names


def _config_for_profile(config: dict[str, Any], name: str) -> dict[str, Any]:
    candidate = deepcopy(config)
    candidate["active_ai_profile"] = name
    candidate["ai"].update(candidate.get("ai_profiles", {})[name])
    return candidate


def _profile_eligibility_failure(config: dict[str, Any]) -> AiFailure | None:
    ai = config.get("ai", {})
    provider = str(ai.get("provider", "none"))
    model = str(ai.get("model") or "")
    if provider == "none":
        return _make_failure(config, "invalid_config", "provider is not configured", False)
    if provider in {"openai", "openai-compatible", "gemini"}:
        if not model:
            return _make_failure(config, "invalid_config", "model is not configured", False)
        env_name = str(ai.get("api_key_env") or "")
        if not env_name or not os.environ.get(env_name):
            return _make_failure(config, "missing_key", f"missing {env_name or 'api_key_env'}", True)
    if provider == "ollama" and not model:
        return _make_failure(config, "invalid_config", "model is not configured", False)
    return None


def _failure_line(failure: AiFailure) -> str:
    status = f"HTTP {failure.status_code} " if failure.status_code is not None else ""
    return f"{failure.profile}: {status}{failure.category} - {failure.message.splitlines()[0]}"


def _all_failed_message(failures: list[AiFailure]) -> str:
    lines = ["All configured AI profiles failed.", "", "Tried:"]
    lines.extend(f"- {_failure_line(failure)}" for failure in failures)
    lines.extend(
        [
            "",
            "Run:",
            "  cairos config ai profiles",
            "  cairos config ai fallback status",
            "  cairos config ai doctor",
        ]
    )
    return "\n".join(lines)


def plan_with_ai_fallback(request: str) -> Plan:
    """Plan with the active AI profile, falling back to other saved profiles."""
    config = load_config()
    ai = config.get("ai", {})
    if not bool(ai.get("auto_fallback", True)):
        return _plan_with_config(request, config)

    names = _fallback_profile_names(config)
    if not names:
        return _plan_with_config(request, config)

    active = str(config.get("active_ai_profile") or names[0])
    persist = bool(ai.get("fallback_persist_switch", True))
    failures: list[AiFailure] = []

    for name in names:
        candidate = _config_for_profile(config, name)
        eligibility = _profile_eligibility_failure(candidate)
        if eligibility is not None:
            failures.append(eligibility)
            continue
        try:
            plan = _plan_with_config(request, candidate)
        except AIPlannerError as exc:
            failure = exc.failure or _make_failure(candidate, "provider_error", str(exc), True)
            failures.append(failure)
            if not failure.recoverable and name == active:
                raise
            continue
        if name != active:
            first_failure = next((failure for failure in failures if failure.profile == active), failures[0] if failures else None)
            notice_lines = ["AI profile fallback:"]
            if first_failure:
                status = f"{first_failure.status_code} " if first_failure.status_code is not None else ""
                notice_lines.append(f"- {active} failed with {status}{first_failure.category}.")
            if persist:
                activate_ai_profile(name)
                notice_lines.append(f"- Switched to {name}.")
                notice_lines.append(f"Active AI profile is now: {name}")
            else:
                notice_lines.append(f"- Used fallback profile for this request only: {name}")
            plan.notices.insert(0, "\n".join(notice_lines))
        return plan

    message = _all_failed_message(failures)
    raise AIPlannerError(message, failure=failures[-1] if failures else None)


def list_models() -> str:
    """List configured provider models without exposing API keys."""
    config = load_config()
    ai = config["ai"]
    provider = ai.get("provider", "none")
    if provider != "gemini":
        return f"Model listing is only implemented for Gemini. Current provider: {provider}"
    endpoint = ai.get("endpoint") or "https://generativelanguage.googleapis.com/v1beta"
    key_env = ai.get("api_key_env") or "GEMINI_API_KEY"
    api_key = os.environ.get(key_env)
    if not api_key:
        return f"{key_env} is not set.\nRun:\n{env_var_setup_hint(key_env)}"
    req = urllib.request.Request(endpoint.rstrip("/") + f"/models?key={api_key}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=int(ai.get("timeout_seconds", 60))) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return f"Could not list Gemini models: HTTP {exc.code}"
    except Exception as exc:
        return f"Could not list Gemini models: {exc.__class__.__name__}"
    names = []
    for item in data.get("models", []):
        methods = item.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            names.append(str(item.get("name", "")).removeprefix("models/"))
    if not names:
        return "No Gemini generateContent models returned for this key."
    return "Gemini generateContent models:\n" + "\n".join(f"- {name}" for name in sorted(names))


def ai_self_test() -> str:
    """Run a tiny configured-AI smoke test and return a safe status message."""
    config = load_config()
    provider = config["ai"].get("provider", "none")
    if provider == "none":
        return "AI test skipped: no AI backend configured."
    try:
        plan = plan_with_ai("Return a no-op plan that prints hello.")
    except AIPlannerError as exc:
        return f"AI test failed safely: {exc}"
    return f"AI test succeeded: provider={provider} source={plan.source} steps={len(plan.steps)}"
