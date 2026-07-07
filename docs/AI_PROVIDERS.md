# CAIROS AI Providers

CAIROS stores environment variable names, never raw API keys. Use
`cairos config ai examples`, `cairos config ai doctor`, and
`cairos config ai test` after configuring a provider.

The optional local GUI exposes the same provider setup and profile management
flows through `cairos gui`; see `docs/GUI.md`.

| Provider | Endpoint | Env var | Notes |
| --- | --- | --- | --- |
| OpenRouter free | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | OpenAI-compatible. `openrouter/free` routes to available free models. Limits and availability can change. |
| Gemini Developer API | `https://generativelanguage.googleapis.com/v1beta` | `GEMINI_API_KEY` | Native CAIROS provider. `gemini-2.5-flash` is the default Flash example. |
| Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | OpenAI-compatible. Groq currently lists `llama-3.1-8b-instant`; check current Groq models if unavailable. |
| OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` | Paid API billing is separate from ChatGPT subscriptions. |
| Mistral | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | Mistral documents chat completions and OpenAI migration guidance. Treat model IDs/limits as current-provider data. |
| Hugging Face Inference Providers | `https://router.huggingface.co/v1` | `HF_TOKEN` | OpenAI-compatible chat endpoint for supported chat completion tasks. Experimental in CAIROS docs. |
| Ollama | `http://localhost:11434` | none | Local provider. Run `ollama serve` and pull a model first. |

## OpenRouter Free

cmd.exe:

```cmd
set OPENROUTER_API_KEY=your-key
cairos config ai use-openrouter-free
cairos config ai test
```

PowerShell:

```powershell
$env:OPENROUTER_API_KEY="your-key"
cairos config ai use-openrouter-free
cairos config ai test
```

Linux/macOS:

```bash
export OPENROUTER_API_KEY="your-key"
cairos config ai use-openrouter-free
cairos config ai test
```

Equivalent explicit command:

```bash
cairos config ai use-openai openrouter/free --endpoint https://openrouter.ai/api/v1 --api-key-env OPENROUTER_API_KEY --profile openrouter-free
```

Some OpenRouter models have `:free` suffixes. Paid models may return HTTP 402
when the account has no credits.

## Gemini

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai test
```

## Groq

```bash
export GROQ_API_KEY="your-key"
cairos config ai use-openai llama-3.1-8b-instant --endpoint https://api.groq.com/openai/v1 --api-key-env GROQ_API_KEY --profile groq-llama
cairos config ai test
```

## OpenAI

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini --api-key-env OPENAI_API_KEY --profile openai-mini
cairos config ai test
```

API usage requires API billing or credits; a ChatGPT subscription is separate.

## Experimental OpenAI-Compatible Providers

Mistral:

```bash
export MISTRAL_API_KEY="your-key"
cairos config ai use-openai mistral-small-latest --endpoint https://api.mistral.ai/v1 --api-key-env MISTRAL_API_KEY --profile mistral-small
```

Hugging Face:

```bash
export HF_TOKEN="your-token"
cairos config ai use-openai <chat-model-id> --endpoint https://router.huggingface.co/v1 --api-key-env HF_TOKEN --profile hf-chat
```

Check each provider's current model catalog, token permissions, billing, rate
limits and free-tier availability before relying on a model.

## Automatic Profile Fallback

CAIROS can keep multiple AI profiles and automatically try another profile when
the active backend is temporarily unusable. Fallback is enabled by default.

```bash
cairos config ai fallback status
cairos config ai fallback enable
cairos config ai fallback disable
cairos config ai fallback order openrouter-free gemini-flash groq-llama
```

Config keys:

```json
{
  "ai": {
    "auto_fallback": true,
    "fallback_order": [],
    "fallback_persist_switch": true
  }
}
```

Fallback triggers for recoverable provider failures such as HTTP 429
rate/quota limits, HTTP 402 insufficient credits, HTTP 502/503/504 temporary
provider errors, network timeouts, auth/key failures where another profile may
work, and model unavailable errors. It does not bypass `cairos run`
confirmation; the final plan still goes through the normal safety and
confirmation flow.
