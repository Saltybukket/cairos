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
from typing import Any

from ..config import load_config
from ..context import collect_context
from ..models import CommandStep, Plan, VerificationStep
from ..rules import load_rules


class AIPlannerError(RuntimeError):
    """Raised when an AI backend is missing, unreachable or returns invalid JSON."""


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
        raise AIPlannerError(f"Ollama backend failed: {exc}") from exc
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
        raise AIPlannerError(f"Missing API key environment variable: {key_env}")
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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
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
        raise AIPlannerError(f"Missing API key environment variable: {key_env}")
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
        if exc.code == 404:
            raise AIPlannerError(
                "The configured Gemini model was not found or is unavailable for this key.\n"
                "Try:\n"
                "  cairos config ai list-models\n"
                "  cairos config ai use-gemini gemini-2.5-flash"
            ) from exc
        if exc.code in {401, 403}:
            raise AIPlannerError("Gemini authentication failed. Check that GEMINI_API_KEY is set and valid.") from exc
        if exc.code == 429:
            raise AIPlannerError("Gemini rate limit or quota reached. Try again later.") from exc
        raise AIPlannerError(f"Gemini backend failed with HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AIPlannerError(f"Gemini backend failed: {exc}") from exc
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_plan(text)


def _custom_command_plan(request: str, config: dict[str, Any]) -> Plan:
    """Call a user-provided local command for planning."""
    command = config["ai"].get("custom_command")
    timeout = int(config["ai"].get("timeout_seconds", 60))
    if not command:
        raise AIPlannerError("custom_command is not configured")
    payload = json.dumps(_build_payload(request))
    proc = subprocess.run(command, input=payload, text=True, shell=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise AIPlannerError(f"custom AI command failed: {proc.stderr.strip()}")
    return _parse_plan(proc.stdout)


def plan_with_ai(request: str) -> Plan:
    """Plan a request with the configured AI provider."""
    config = load_config()
    provider = config["ai"].get("provider", "none")
    if provider == "none":
        raise AIPlannerError("No AI backend configured")
    if provider == "ollama":
        return _ollama_plan(request, config)
    if provider in {"openai", "openai-compatible"}:
        return _openai_compatible_plan(request, config)
    if provider == "gemini":
        return _gemini_plan(request, config)
    if provider == "custom-command":
        return _custom_command_plan(request, config)
    raise AIPlannerError(f"Unsupported AI provider: {provider}")


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
        return f"{key_env} is not set.\nRun:\n  export {key_env}=\"...\""
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
