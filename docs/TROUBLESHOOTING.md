# CAIROS Troubleshooting

This file lists common CAIROS setup and usage problems with fixes.

For AI provider HTTP errors, see `docs/TROUBLESHOOTING_AI.md`.
For updates and config backups, see `docs/UPDATING.md`.
For the optional local web GUI, see `docs/GUI.md`.

## `cairos` command not found

Recommended install:

```bash
pipx install git+https://github.com/Saltybukket/cairos.git
```

Check installation details:

```bash
cairos install-info
```

Ensure `~/.local/bin` is on `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

On Windows PowerShell, run:

```powershell
py -m pipx ensurepath
```

Restart the terminal after changing `PATH`.

## No deterministic match

Configure AI or add a template:

```bash
cairos config ai list-providers
cairos config ai use-ollama llama3.1 --profile ollama-local
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
```

## Template matched the wrong thing

Use route debugging:

```bash
cairos plan --debug-route <task>
```

If the task is fuzzy or broad, simplify it or configure AI fallback:

```bash
cairos config ai status
cairos config ai use-profile openrouter-free
```

For directory search, bypass natural language parsing:

```bash
cairos find-dir "oop ss26"
```

## Gemini model not found

```bash
cairos config ai list-models
cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
```

## Gemini key missing

Bash/zsh/WSL:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai test
```

PowerShell:

```powershell
$env:GEMINI_API_KEY="your-key"
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")
cairos config ai test
```

cmd.exe:

```cmd
set GEMINI_API_KEY=your-key
setx GEMINI_API_KEY "your-key"
cairos config ai test
```

Switch to another saved profile:

```bash
cairos config ai profiles
cairos config ai switch
```

## Check command did the wrong thing

Shell safety:

```bash
cairos check git push --force
```

Natural language:

```bash
cairos -- check the commit log and summarize it
```

## Windows and WSL

Install inside the WSL distribution where you want to use CAIROS. Windows can
edit files through the UNC path, but the `cairos` executable should run inside
WSL for WSL projects.

VS Code may auto-activate a Python `.venv` in terminals. That is unrelated to
CAIROS installed with pipx. Disable it with:

```json
{
  "python.terminal.activateEnvironment": false
}
```

## Shell helper

`cairos shell install zsh` currently prints an optional zsh snippet. It does not
modify `~/.zshrc` unless a future version asks for confirmation.

## GUI dependencies missing

Install optional GUI dependencies:

```bash
pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart
```

For editable development installs:

```bash
python -m pip install -e ".[gui]"
```

Then run:

```bash
cairos gui --check
```
