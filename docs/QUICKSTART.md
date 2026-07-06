# CAIROS Quickstart

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

## First Commands

```bash
cairos quicksetup
cairos doctor
cairos templates
cairos templates system
cairos context
```

Direct task commands plan only:

```bash
cairos create folder docs
```

Execution is explicit:

```bash
cairos run create folder docs
```

## Files CAIROS Uses

Linux/macOS/WSL:

```text
~/.config/cairos/config.json
~/.local/state/cairos/history.jsonl
```

Windows:

```text
%APPDATA%\cairos\config.json
%LOCALAPPDATA%\cairos\history.jsonl
```

Optional project-local rules:

```text
.cairos/rules.json
```
