# CAIROS

**CAIROS - Context-Aware Intelligent Runtime Operating Shell**

CAIROS is a context-aware command assistant that lives inside your normal shell.
It is not a replacement for zsh, bash, PowerShell, or fish. Install the package
once, then use the `cairos` command from any project directory.

Package name: `cairos-shell`  
Command name: `cairos`

## TL;DR

```bash
pipx install cairos-shell
cairos quicksetup
cd your-project
cairos doctor
```

On Windows PowerShell:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
pipx install cairos-shell
cairos quicksetup
```

## Everyday Use

```bash
cairos check if repo is ready to commit
cairos plan create bash script branch_info that prints current git branch and folder
cairos plan create cpp mini project new_cpp_project with class TestSubject and main
cairos run create folder docs
```

Direct `cairos <task>` prints a plan. Use `cairos run <task>` to execute after
confirmation.

CAIROS first tries deterministic templates with typo-tolerant matching. If no
template can satisfy the request, it can fall back to a configured AI backend.

## Install Options

Recommended user install:

```bash
pipx install cairos-shell
```

Development checkout:

```bash
pipx install --editable .
```

GitHub install:

```bash
pipx install git+https://github.com/<user>/<repo>.git
```

Fallback:

```bash
python -m pip install --user cairos-shell
```

## Key Locations

Global config:

```text
~/.config/cairos/config.json
```

History:

```text
~/.local/state/cairos/history.jsonl
```

Optional project-local rules:

```text
.cairos/rules.json
```

On Windows, CAIROS uses `%APPDATA%\cairos\config.json` and
`%LOCALAPPDATA%\cairos\history.jsonl`.

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [User Guide](docs/USER_GUIDE.md)
- [AI Setup](docs/AI_SETUP.md)
- [Safety](docs/SAFETY.md)
- [Developer Guide](docs/DEVELOPER.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
