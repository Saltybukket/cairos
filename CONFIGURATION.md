# CAIROS Configuration

Global config:

```text
~/.config/cairos/config.json
```

Global state and history:

```text
~/.local/state/cairos/history.jsonl
```

Project rules:

```text
.cairos/rules.json
```

Initialize:

```bash
cairos init
cairos init --global
cairos setup
```

AI:

```bash
cairos config ai use-ollama llama3.1
cairos config ai use-gemini gemini-2.5-flash
cairos config ai use-openai gpt-4.1-mini
cairos config ai use-custom python3 ~/planner.py
cairos config ai test
cairos config ai list-models
```

CAIROS stores environment variable names, never raw API keys.
