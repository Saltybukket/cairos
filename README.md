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

Optional Gemini setup:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash
cairos config ai test
```

## Windows PowerShell

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install git+https://github.com/Saltybukket/cairos.git
cairos quicksetup
```

Gemini:

```powershell
setx GEMINI_API_KEY "your-key"
$env:GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash
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
cairos templates system
cairos plan create cpp mini project engine with class Player and main
cairos plan list wsl distros
cairos plan open project in vscode
cairos run create folder docs
```

Direct `cairos <task>` prints a plan. Use `cairos run <task>` to execute after
confirmation.

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
- [Safety](docs/SAFETY.md)
- [Release Guide](docs/RELEASE.md)
- [Developer Guide](docs/DEVELOPER.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
