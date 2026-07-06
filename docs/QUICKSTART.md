# CAIROS Quickstart

CAIROS installs like a normal console helper. You install it once, then run
`cairos` from any directory.

The PyPI package is `cairos-shell`; the terminal command is `cairos`.

## Linux, macOS, and WSL

Install `pipx` if needed:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Install CAIROS:

```bash
pipx install cairos-shell
cairos quicksetup
```

If `cairos` is not found, make sure `~/.local/bin` is on `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

For bash:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Windows PowerShell

Install `pipx` if needed:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Restart PowerShell, then install CAIROS:

```powershell
pipx install cairos-shell
cairos quicksetup
```

`cairos quicksetup` prints the command path, config path, history path, PATH
status, and AI setup suggestions without requiring pipx internals.

## Development and GitHub Installs

From a source checkout:

```bash
pipx install --editable .
cairos install-info
```

From GitHub:

```bash
pipx install git+https://github.com/<user>/<repo>.git
```

Fallback without pipx:

```bash
python -m pip install --user cairos-shell
```

## First Commands

```bash
cairos quicksetup
cairos doctor
cairos context
cairos check if repo is ready to commit
```

Direct task commands plan only:

```bash
cairos create folder docs
```

Execution is explicit:

```bash
cairos run create folder docs
```

## AI Choices

Use CAIROS without AI:

```bash
cairos config ai disable
```

Use Gemini:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash
cairos config ai test
```

PowerShell:

```powershell
setx GEMINI_API_KEY "your-key"
cairos config ai use-gemini gemini-2.5-flash
```

Use Ollama:

```bash
ollama pull llama3.1
cairos config ai use-ollama llama3.1
```

Use OpenAI-compatible APIs:

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
```

## Files CAIROS Uses

Global config on Linux/macOS/WSL:

```text
~/.config/cairos/config.json
```

History on Linux/macOS/WSL:

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
