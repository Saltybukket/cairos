"""Safe, testable actions used by the optional CAIROS GUI."""

from __future__ import annotations

from ..ai import ai_self_test
from ..config import activate_ai_profile, backup_config as backup_config_file, configure_gemini, configure_ollama, configure_openai, delete_ai_profile, rename_ai_profile, set_ai_fallback
from .schemas import ActionResult
from .security import mask_secret_text


def switch_profile(profile_name: str) -> ActionResult:
    try:
        activate_ai_profile(profile_name)
    except KeyError:
        return ActionResult(False, f"Unknown AI profile: {profile_name}", "error")
    return ActionResult(True, f"Activated AI profile: {profile_name}")


def create_openrouter_free_profile(profile_name: str = "openrouter-free") -> ActionResult:
    configure_openai("openrouter/free", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", profile=profile_name)
    return ActionResult(True, f"Created OpenRouter free profile: {profile_name}")


def create_gemini_profile(profile_name: str = "gemini-flash", model: str = "gemini-2.5-flash", api_key_env: str = "GEMINI_API_KEY") -> ActionResult:
    configure_gemini(model=model or "gemini-2.5-flash", api_key_env=api_key_env or "GEMINI_API_KEY", profile=profile_name or "gemini-flash")
    return ActionResult(True, f"Created Gemini profile: {profile_name or 'gemini-flash'}")


def create_groq_profile(profile_name: str = "groq-llama", model: str = "llama-3.1-8b-instant", api_key_env: str = "GROQ_API_KEY") -> ActionResult:
    configure_openai(model or "llama-3.1-8b-instant", api_key_env or "GROQ_API_KEY", "https://api.groq.com/openai/v1", profile=profile_name or "groq-llama")
    return ActionResult(True, f"Created Groq profile: {profile_name or 'groq-llama'}")


def create_openai_profile(profile_name: str = "openai-mini", model: str = "gpt-4.1-mini", api_key_env: str = "OPENAI_API_KEY", endpoint: str = "https://api.openai.com/v1") -> ActionResult:
    configure_openai(model or "gpt-4.1-mini", api_key_env or "OPENAI_API_KEY", endpoint or "https://api.openai.com/v1", profile=profile_name or "openai-mini")
    return ActionResult(True, f"Created OpenAI-compatible profile: {profile_name or 'openai-mini'}")


def create_ollama_profile(profile_name: str = "ollama-local", model: str = "llama3.1", endpoint: str = "http://localhost:11434") -> ActionResult:
    configure_ollama(model or "llama3.1", endpoint or "http://localhost:11434", profile=profile_name or "ollama-local")
    return ActionResult(True, f"Created Ollama profile: {profile_name or 'ollama-local'}")


def rename_profile(old_name: str, new_name: str) -> ActionResult:
    try:
        rename_ai_profile(old_name, new_name)
    except KeyError:
        return ActionResult(False, f"Unknown AI profile: {old_name}", "error")
    return ActionResult(True, f"Renamed profile: {old_name} -> {new_name}")


def remove_profile(profile_name: str, force: bool = False) -> ActionResult:
    try:
        delete_ai_profile(profile_name, force=force)
    except ValueError:
        return ActionResult(False, "Cannot delete the active profile unless force is enabled.", "warning")
    except KeyError:
        return ActionResult(False, f"Unknown AI profile: {profile_name}", "error")
    return ActionResult(True, f"Deleted AI profile: {profile_name}")


def backup_config() -> ActionResult:
    backup = backup_config_file()
    if backup is None:
        return ActionResult(True, "No config exists yet; nothing to back up.", "info")
    return ActionResult(True, f"Created config backup: {backup}")


def toggle_auto_fallback(enabled: bool) -> ActionResult:
    set_ai_fallback(enabled=enabled)
    return ActionResult(True, f"Auto fallback {'enabled' if enabled else 'disabled'}.")


def toggle_persist_switch(enabled: bool) -> ActionResult:
    set_ai_fallback(persist_switch=enabled)
    return ActionResult(True, f"Fallback profile switch persistence {'enabled' if enabled else 'disabled'}.")


def set_fallback_order(names: list[str]) -> ActionResult:
    set_ai_fallback(order=names)
    return ActionResult(True, "Updated fallback order.")


def run_ai_doctor() -> ActionResult:
    return ActionResult(True, mask_secret_text(ai_self_test()), "info")
