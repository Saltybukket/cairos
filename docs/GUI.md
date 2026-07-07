# CAIROS Local Web GUI

CAIROS includes an optional local browser GUI launched with:

```bash
cairos gui
```

The GUI uses FastAPI, HTMX, Jinja2, and Tailwind through CDNs. It does not use
React, Electron, Node, Vite, npm, or a frontend build step.

## Install GUI Dependencies

For pipx installs:

```bash
pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart
```

Future PyPI extra:

```bash
pipx install "cairos-shell[gui]"
```

Editable development install:

```bash
python -m pip install -e ".[gui]"
```

## Launch

```bash
cairos gui
cairos gui --no-open
cairos gui --host 127.0.0.1 --port 0
cairos gui --debug
```

`--port 0` chooses a free random local port. `--no-open` prints the URL without
opening a browser.

## Headless Check

```bash
cairos gui --check
```

The check prints dependency availability, config readability, loaded profile
count, and GUI state status. It exits without starting a long-running server.

## Security Model

- The GUI binds only to local hosts such as `127.0.0.1`.
- Binding to `0.0.0.0` is refused.
- Each launch creates a temporary session token.
- State-changing POST routes require the token.
- Cross-origin POST requests are rejected.
- The GUI does not execute arbitrary shell commands.
- Raw API keys are never stored or displayed.

The GUI may show `OPENROUTER_API_KEY: available`, but it never prints the
environment variable value.

## Pages

- Overview: version, command path, config path, history path, project rules,
  platform, shell, active profile, fallback status.
- AI Profiles: saved profiles, active marker, provider, model, endpoint, key
  environment variable availability, activate action.
- Add Provider: OpenRouter free, Gemini, Groq, OpenAI-compatible, and Ollama
  profile forms.
- Fallback: auto fallback, persisted switch behavior, fallback order.
- Doctor: local diagnostics and safe AI self-test output.
- Updates: version, update commands, config backup.

## Supported Actions

- switch active profile
- create OpenRouter free profile
- create Gemini profile
- create Groq profile
- create OpenAI-compatible profile
- create Ollama profile
- toggle auto fallback
- toggle fallback switch persistence
- update fallback order
- run AI test/doctor
- back up config

## Troubleshooting

If dependencies are missing:

```text
CAIROS GUI dependencies are not installed.
```

Install the GUI dependencies, then run:

```bash
cairos gui --check
```

If the browser does not open automatically, use:

```bash
cairos gui --no-open
```

and paste the printed local URL into a browser.

## Headless Testing Notes

Tests for state, actions, token protection, and dependency checks do not need a
display server. FastAPI route tests are skipped unless the optional GUI
dependencies are installed.

## Known Limitations

- The first GUI version does not execute CAIROS plans.
- It does not run arbitrary shell commands.
- It does not edit OS environment variables.
- Delete, duplicate, and rename profile controls are kept in service functions
  for future UI expansion but are not all exposed as primary buttons yet.
