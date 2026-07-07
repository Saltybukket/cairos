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
python -m pip install -e ".[gui,dev]"
```

## Launch

```bash
cairos gui
cairos gui --no-open
cairos gui --host 127.0.0.1 --port 0
cairos gui --debug
```

`--port 0` chooses a free random local port. `--no-open` prints the URL without
opening a browser. Supported bind hosts are `127.0.0.1` and `localhost`.

## Headless Check

```bash
cairos gui --check
```

The check prints dependency availability, including `python-multipart` for form
POST parsing, config readability, loaded profile count, and GUI state status.
It exits without starting a long-running server.

## Security Model

- The GUI binds only to local hosts: `127.0.0.1` or `localhost`.
- Binding to `0.0.0.0` is refused.
- Each launch creates a temporary session token.
- State-changing POST routes require the token.
- Cross-origin POST requests are rejected.
- Responses include `Referrer-Policy`, `Cache-Control`, `X-Frame-Options`, and
  `X-Content-Type-Options` security headers.
- The GUI does not execute arbitrary shell commands.
- Raw API keys are never stored or displayed.

The GUI field "Environment variable name" is not the API key. It stores a name
such as `OPENROUTER_API_KEY`. Use the API Key Setup section to set the real key
for the current GUI session or generate terminal commands.

Actual key values are hidden by default. Use Reveal key only when you
intentionally want to display or copy the current environment value. Revealed
keys appear on screen and should not be exposed during screen sharing.

Current-session key setup affects only the running GUI process. Persistent
shell or OS setup may require opening a new terminal.

## Pages

- Overview: version, command path, config path, history path, project rules,
  platform, shell, active profile, fallback status.
- AI Profiles: saved profiles, active marker, provider, model, endpoint, key
  variable status, profile edit forms, reveal action, and current-session key
  setup.
- Add Provider: OpenRouter free, Gemini, Groq, OpenAI-compatible, and Ollama
  profile forms.
- Fallback: auto fallback, persisted switch behavior, fallback order.
- Doctor: local diagnostics and safe AI self-test output.
- Updates: version, update commands, config backup.

## Supported Actions

- switch active profile
- edit profile name, model, endpoint, and environment variable name
- set a real key value for the current GUI session
- generate shell setup commands with a placeholder or explicit pasted value
- reveal a current environment key value only after an explicit POST action
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
