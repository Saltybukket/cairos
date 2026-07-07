# CAIROS AI Setup

This file explains optional AI backends for CAIROS.

CAIROS works without AI. Configure a backend only when deterministic templates
do not cover your workflow.

See also: `docs/AI_PROVIDERS.md`, `docs/TROUBLESHOOTING_AI.md` and
`docs/WINDOWS.md`.

## API Key Concepts

CAIROS separates two things:

1. The environment variable name, for example `OPENROUTER_API_KEY`.
2. The actual secret API key value.

CAIROS profiles store only the environment variable name. The real key lives in
your shell or operating system environment. The GUI and CLI can reveal or print
a key value only when you explicitly ask for it.

## Recommended Setup Flow

1. Create or select a provider profile.
2. Choose or accept the suggested environment variable name.
3. Set the actual API key value in your terminal or through the local GUI.
4. Reveal or print the key only when you intentionally need to copy or debug it.
5. Restart the terminal if you used persistent environment commands.
6. Run `cairos config ai test`.

Helpful CLI commands:

```bash
cairos config ai key status OPENROUTER_API_KEY
cairos config ai key commands OPENROUTER_API_KEY --shell bash
cairos config ai key commands OPENROUTER_API_KEY --shell powershell
cairos config ai key reveal OPENROUTER_API_KEY
cairos config ai key reveal OPENROUTER_API_KEY --raw --yes
```

Reveal and print commands intentionally display secrets in your terminal. Do not
paste that output into chats, issues, logs, or screenshots.

## OpenRouter Free

```bash
export OPENROUTER_API_KEY="your-key"
cairos config ai use-openrouter-free
cairos config ai test
```

OpenRouter model availability and free limits can change. `openrouter/free` is
a convenient router for free models.

## Disable AI

```bash
cairos config ai disable
```

## Ollama

```bash
cairos config ai use-ollama llama3.1 --profile ollama-local
ollama pull llama3.1
ollama serve
```

Optional endpoint:

```bash
cairos config ai set-ollama-endpoint http://localhost:11434
```

## Gemini

Store the key only in your environment:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai status
cairos config ai test
```

PowerShell:

```powershell
$env:GEMINI_API_KEY="your-key"
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
```

cmd.exe:

```cmd
set GEMINI_API_KEY=your-key
setx GEMINI_API_KEY "your-key"
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
```

CAIROS never writes the raw key to config, logs, reports or docs.

List models available to the current key:

```bash
cairos config ai list-models
```

If Gemini returns a 404, the configured model is unavailable for that key. Run:

```bash
cairos config ai list-models
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
```

## OpenAI-Compatible API

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini --profile openai-mini
cairos config ai set-openai-endpoint https://api.openai.com/v1
```

Custom environment variable:

```bash
cairos config ai use-openai gpt-4.1-mini --api-key-env MY_API_KEY --profile openai-mini
```

## AI Profiles

Save multiple providers/models and switch quickly:

```bash
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai use-openai gpt-4.1-mini --profile openai-mini
cairos config ai use-ollama llama3.1 --profile ollama-local

cairos config ai profiles
cairos config ai switch
cairos config ai use-profile openai-mini
```

CAIROS stores only environment variable names in profiles, never raw API keys.

## Custom Command

```bash
cairos config ai use-custom python3 ~/my_cairos_planner.py
```

The command reads JSON on stdin and prints validated CAIROS plan JSON on stdout.

## AI Safety

AI-generated risk labels are not trusted blindly. CAIROS validates the JSON,
converts it to structured steps, runs the normal safety scanner, and executes
only through `cairos run ...` with confirmation.
