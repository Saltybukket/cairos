# CAIROS

**CAIROS — Context-Aware Intelligent Runtime Operating Shell**

CAIROS is a context-aware command assistant that lives inside your normal shell. It is **not** a replacement for zsh, bash or fish. Install the package `cairos-shell` once, then use the `cairos` command from any directory.

```bash
cairos macke python projekt demo mit venv git pytest
cairos create cpp header file Player
cairos make folder docs
cairos --dry-run create python project demo
cairos preview create cpp header Player
cairos diff create cpp header Player
cairos explain git reset --soft HEAD~1
cairos config ai use-ollama llama3.1
cairos config ai use-gemini gemini-2.5-flash
cairos config ai list-models
cairos check if repo is ready to commit
cairos plan create bash script branch_info that prints current git branch and folder
cairos plan create cpp mini project new_cpp_project with class TestSubject and main
```

CAIROS first tries deterministic templates with typo-tolerant matching. Direct `cairos <task>` only prints a plan; use `cairos run <task>` to execute after confirmation. Only when it cannot solve a request locally does it fall back to a configured AI backend.

## Quick start for development

```bash
pipx install --editable .
cairos --version
make test
make check
```

## Install as a console helper

Recommended:

```bash
pipx install cairos-shell
cairos setup
```

From GitHub:

```bash
pipx install git+https://github.com/<user>/<repo>.git
```

Fallback:

```bash
python -m pip install --user cairos-shell
```

After installation, `cairos` can be used from any folder.

## Local AI setup

```bash
cairos config ai use-ollama llama3.1
ollama pull llama3.1
ollama serve
```

## API setup

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
```

Gemini:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash
cairos config ai test
```

See [`DOCUMENTATION.md`](DOCUMENTATION.md) for full commands, settings and behavior.

Additional references:

- [`TEMPLATES.md`](TEMPLATES.md) lists deterministic tasks.
- [`SAFETY.md`](SAFETY.md) explains risk levels and blocked commands.
- [`AI_SETUP.md`](AI_SETUP.md) covers Ollama, Gemini, OpenAI-compatible APIs and custom commands.
- [`DEPENDENCIES.md`](DEPENDENCIES.md) lists runtime and optional dependencies.
