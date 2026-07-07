"""Pure state loading helpers for the optional CAIROS GUI."""

from __future__ import annotations

import os
import platform
import shutil

from .. import __version__
from ..config import ai_fallback_settings, ai_profiles, active_ai_profile_name, config_path, load_config, shell_guess
from ..history import history_path
from ..rules import local_rules_path
from .schemas import DoctorItem, GuiProfile, GuiState, ProviderPreset


PROVIDER_PRESETS = [
    ProviderPreset("openrouter-free", "OpenRouter Free", "openai", "openrouter/free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "Free OpenRouter routing profile."),
    ProviderPreset("openrouter-custom", "OpenRouter Custom", "openai", "openrouter/free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "Custom OpenRouter model slug."),
    ProviderPreset("gemini", "Gemini", "gemini", "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "Google Gemini Developer API."),
    ProviderPreset("groq", "Groq", "openai", "llama-3.1-8b-instant", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "Groq OpenAI-compatible endpoint."),
    ProviderPreset("openai", "OpenAI", "openai", "gpt-4.1-mini", "https://api.openai.com/v1", "OPENAI_API_KEY", "OpenAI chat completions endpoint."),
    ProviderPreset("ollama", "Ollama Local", "ollama", "llama3.1", "http://localhost:11434", "", "Local Ollama provider."),
    ProviderPreset("custom-openai-compatible", "Custom OpenAI-Compatible", "openai", "", "", "OPENAI_API_KEY", "Any OpenAI-compatible chat completions endpoint."),
]


def _profile_to_gui(name: str, profile: dict[str, object], active: str) -> GuiProfile:
    provider = str(profile.get("provider") or "none")
    env_name = str(profile.get("api_key_env") or "")
    local = provider in {"ollama", "custom-command"} or not env_name
    return GuiProfile(
        name=name,
        active=name == active,
        provider=provider,
        model=str(profile.get("model") or ""),
        endpoint=str(profile.get("endpoint") or ""),
        api_key_env=env_name,
        key_available=True if local else bool(os.environ.get(env_name)),
        local=local,
    )


def load_gui_state() -> GuiState:
    """Return all non-secret state needed by the GUI."""
    config = load_config()
    active = active_ai_profile_name()
    profiles = [_profile_to_gui(name, profile, active) for name, profile in sorted(ai_profiles().items())]
    fallback = ai_fallback_settings()
    doctor_items = build_doctor_items(config, profiles, fallback)
    return GuiState(
        version=__version__,
        command_path=shutil.which("cairos") or "<not found on PATH>",
        config_path=str(config_path()),
        history_path=str(history_path()),
        project_rules_path=str(local_rules_path()),
        platform=platform.system() or "unknown",
        shell=shell_guess(),
        active_profile=active or "<none>",
        profiles=profiles,
        fallback_enabled=bool(fallback["auto_fallback"]),
        fallback_order=list(fallback["fallback_order"]),
        fallback_persist_switch=bool(fallback["fallback_persist_switch"]),
        config_schema_version=int(config.get("schema_version", 0) or 0),
        doctor_items=doctor_items,
    )


def build_doctor_items(config: dict[str, object], profiles: list[GuiProfile], fallback: dict[str, object]) -> list[DoctorItem]:
    """Build lightweight diagnostics without running external commands."""
    ai = config.get("ai", {}) if isinstance(config.get("ai"), dict) else {}
    active = str(config.get("active_ai_profile") or "")
    active_profile = next((profile for profile in profiles if profile.name == active), None)
    env_name = str(ai.get("api_key_env") or "") if isinstance(ai, dict) else ""
    endpoint = str(ai.get("endpoint") or "") if isinstance(ai, dict) else ""
    return [
        DoctorItem("Config readable", "ok", str(config_path())),
        DoctorItem("Config schema", "ok" if config.get("schema_version") else "warning", str(config.get("schema_version") or "<missing>")),
        DoctorItem("Active profile", "ok" if active_profile else "warning", active or "<none>"),
        DoctorItem("AI key env", "ok" if (not env_name or os.environ.get(env_name)) else "warning", f"{env_name or 'none'}: {'available' if env_name and os.environ.get(env_name) else 'missing' if env_name else 'not required'}"),
        DoctorItem("Provider endpoint", "ok" if endpoint or str(ai.get("provider", "none")) in {"none", "ollama"} else "warning", endpoint or "<not set>"),
        DoctorItem("Fallback", "ok" if fallback.get("auto_fallback") else "warning", "enabled" if fallback.get("auto_fallback") else "disabled"),
        DoctorItem("PATH", "ok" if shutil.which("cairos") else "warning", shutil.which("cairos") or "cairos not found on PATH"),
        DoctorItem("GUI binding", "ok", "127.0.0.1 only by default"),
    ]

