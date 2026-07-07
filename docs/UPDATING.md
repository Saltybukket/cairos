# Updating CAIROS

Run:

```bash
cairos update
```

CAIROS prints the recommended update command for the current install mode.

If you use the optional GUI through pipx injection, update CAIROS first and then
re-run the injection command if the pipx environment was recreated:

```bash
pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart
```

## GitHub pipx Install

Current public install:

```bash
pipx install git+https://github.com/Saltybukket/cairos.git
```

Update:

```bash
cairos update
pipx upgrade cairos-shell
cairos doctor
cairos config ai profiles
```

If pipx cannot upgrade the VCS install on your machine, reinstall the package
environment:

```bash
pipx uninstall cairos-shell
pipx install git+https://github.com/Saltybukket/cairos.git
```

This removes the pipx package environment only. It does not remove CAIROS user
config, history, AI profiles, environment variable names, or project rules.

## Future PyPI Install

There is no PyPI release yet. Future command:

```bash
pipx install cairos-shell
pipx upgrade cairos-shell
```

## Preserved Files

Windows:

```text
%APPDATA%\cairos\config.json
%LOCALAPPDATA%\cairos\history.jsonl
```

Linux/macOS/WSL:

```text
~/.config/cairos/config.json
~/.local/state/cairos/history.jsonl
```

Project rules:

```text
.cairos/rules.json
```

## Backup and Migration

```bash
cairos backup-config
cairos config migrate
```

Migrations preserve existing values, unknown keys, AI profiles, active profile,
custom endpoints and API key environment variable names. Raw API keys should not
be stored in CAIROS config.
