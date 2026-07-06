# CAIROS AI Setup

CAIROS works without AI. Configure a backend only when deterministic templates
do not cover your workflow.

## Disable AI

```bash
cairos config ai disable
```

## Ollama

```bash
cairos config ai use-ollama llama3.1
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
cairos config ai use-gemini gemini-1.5-flash
cairos config ai status
```

CAIROS never writes the raw key to config, logs, reports or docs.

## OpenAI-Compatible API

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
cairos config ai set-openai-endpoint https://api.openai.com/v1
```

Custom environment variable:

```bash
cairos config ai use-openai gpt-4.1-mini --api-key-env MY_API_KEY
```

## Custom Command

```bash
cairos config ai use-custom python3 ~/my_cairos_planner.py
```

The command reads JSON on stdin and prints validated CAIROS plan JSON on stdout.
