"""Shared AI provider setup presets."""

from __future__ import annotations

from .gui.schemas import ProviderPreset


PROVIDER_PRESETS = [
    ProviderPreset("openrouter-free", "OpenRouter Free", "openai", "openrouter/free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "Free OpenRouter routing profile."),
    ProviderPreset("openrouter-custom", "OpenRouter Custom", "openai", "openrouter/free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "Custom OpenRouter model slug."),
    ProviderPreset("gemini", "Gemini", "gemini", "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "Google Gemini Developer API."),
    ProviderPreset("groq", "Groq", "openai", "llama-3.1-8b-instant", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "Groq OpenAI-compatible endpoint."),
    ProviderPreset("openai", "OpenAI", "openai", "gpt-4.1-mini", "https://api.openai.com/v1", "OPENAI_API_KEY", "OpenAI chat completions endpoint."),
    ProviderPreset("ollama", "Ollama Local", "ollama", "llama3.1", "http://localhost:11434", "", "Local Ollama provider."),
    ProviderPreset("custom-openai-compatible", "Custom OpenAI-Compatible", "openai", "", "", "OPENAI_API_KEY", "Any OpenAI-compatible chat completions endpoint."),
]
