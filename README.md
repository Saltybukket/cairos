# CAIROS

**CAIROS - Context-Aware Intelligent Runtime Operating Shell**

CAIROS is a context-aware console assistant that lives inside your normal shell.
It is useful offline through deterministic templates, and can use AI as a
fallback when configured.

Package/distribution name: `cairos-shell`  
Terminal command: `cairos`  
GitHub repo: `Saltybukket/cairos`

## Quickstart

Install from GitHub:

```bash
pipx install git+https://github.com/Saltybukket/cairos.git
cairos quicksetup
```

Use from any project:

```bash
cd ~/projects/my_repo
cairos doctor
cairos context
cairos check if repo is ready to commit
```

OpenRouter free quickstart:

```bash
export OPENROUTER_API_KEY="your-key"
cairos config ai use-openrouter-free
cairos config ai test
```

Optional Gemini setup:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai test
```

## Windows PowerShell

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install git+https://github.com/Saltybukket/cairos.git
cairos quicksetup
```

Gemini in PowerShell:

```powershell
$env:GEMINI_API_KEY="your-key"
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai test
```

Gemini in cmd.exe:

```cmd
set GEMINI_API_KEY=your-key
setx GEMINI_API_KEY "your-key"
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
cairos config ai test
```

## Future PyPI Install

There is no PyPI release yet. After CAIROS is published to PyPI, installation
will be:

```bash
pipx install cairos-shell
```

## Development Install

```bash
git clone https://github.com/Saltybukket/cairos.git
cd cairos
pipx install --editable .
cairos install-info
```

## Everyday Use

```bash
cairos
cairos templates
cairos gui --check
cairos gui
cairos templates system
cairos plan create cpp mini project engine with class Player and main
cairos plan list wsl distros
cairos plan open project in vscode
cairos run create folder docs
```

Direct `cairos <task>` prints a plan. Use `cairos run <task>` to execute after
confirmation.

## Optional Local Web GUI

Install the optional GUI dependencies, then launch a localhost-only dashboard:

```bash
pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart
cairos gui --check
cairos gui
```

For editable development installs:

```bash
python -m pip install -e ".[gui]"
```

The GUI shows config paths, AI profiles, provider setup, fallback settings,
doctor output, and update/backup guidance. It binds locally, uses a temporary
session token for state-changing POST requests, and never displays raw API keys.

## Templates vs AI

Simple, clear commands use offline deterministic templates. Longer fuzzy
requests are scored for confidence; low-confidence templates step back so AI
fallback can handle the request when configured. Every template or AI plan is
still safety-scanned before display or execution.

Debug routing decisions with:

```bash
cairos plan --debug-route <task>
```

CAIROS cannot permanently change the parent shell directory from a child
process. Use `cairos find-dir <name>` or a shell wrapper from
[Shell Navigation](docs/SHELL_NAVIGATION.md) for `cd` workflows.

## Update

```bash
cairos update
cairos backup-config
```

GitHub installs are updated with the command printed by `cairos update`.
Config, history and AI profiles live outside the package install and are
preserved across package upgrades.

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

Automatic profile fallback is enabled by default. If the active profile is
rate-limited, out of credits, temporarily unavailable, missing a visible key, or
points at an unavailable model, CAIROS tries another saved profile and prints a
notice before the plan:

```bash
cairos config ai fallback status
cairos config ai fallback disable
cairos config ai fallback enable
cairos config ai fallback order openrouter-free gemini-flash groq-llama
```

CAIROS stores environment variable names, never raw API keys.

## Key Locations

Linux/macOS/WSL config:

```text
~/.config/cairos/config.json
```

Linux/macOS/WSL history:

```text
~/.local/state/cairos/history.jsonl
```

Windows config:

```text
%APPDATA%\cairos\config.json
```

Windows history:

```text
%LOCALAPPDATA%\cairos\history.jsonl
```

Optional project-local rules:

```text
.cairos/rules.json
```

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [User Guide](docs/USER_GUIDE.md)
- [AI Setup](docs/AI_SETUP.md)
- [AI Providers](docs/AI_PROVIDERS.md)
- [Local Web GUI](docs/GUI.md)
- [Windows Guide](docs/WINDOWS.md)
- [Shell Navigation](docs/SHELL_NAVIGATION.md)
- [Request Router](docs/ROUTER.md)
- [AI Troubleshooting](docs/TROUBLESHOOTING_AI.md)
- [Updating](docs/UPDATING.md)
- [Safety](docs/SAFETY.md)
- [Release Guide](docs/RELEASE.md)
- [Developer Guide](docs/DEVELOPER.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
