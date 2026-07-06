# CAIROS Documentation

**CAIROS** means **Context-Aware Intelligent Runtime Operating Shell**.

CAIROS is a command-line assistant that runs inside your normal terminal. It is meant to support work in other projects without getting in the way. You install it once, then call `cairos ...` from any project folder.

---

## 1. Design goal

CAIROS should be useful even without AI.

Pipeline:

```text
user request
  -> normalize text and tolerate small typos
  -> collect compact context
  -> try deterministic templates
  -> if no template matches, try configured AI backend
  -> scan the plan for risky commands
  -> print the exact planned steps
  -> execute only after confirmation
  -> verify results
```

The AI is a fallback, not the main engine.

---

## 2. Installation

### Development install

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cairos --version
```

### Normal local install

```bash
python -m pip install .
```

### Recommended user install with `pipx`

```bash
pipx install .
```

Then `cairos` is available in your shell from any folder.

---

## 3. Basic usage

Main style:

```bash
cairos <task in natural language>
```

Examples:

```bash
cairos make folder docs
cairos macke ordner docs
cairos create python project crawler with venv git pytest
cairos mache python projekt crawler mit venv git pytest
cairos create cpp project engine with cmake
cairos create cpp header file Player
cairos clean pycache
cairos find large files
cairos run tests
cairos finish current branch and prepare push to origin main
```

CAIROS accepts unquoted text because your shell passes the words as separate arguments and CAIROS joins them internally.

---

## 4. Reserved commands

Some commands are explicit modes:

```bash
cairos plan <task>
cairos expand <task>
cairos run <task> [--yes]
cairos explain <shell command>
cairos check <shell command>
cairos context [--json]
cairos config ...
cairos rules ...
cairos doctor
cairos history
cairos --dry-run <task>
cairos preview <task>
cairos diff <task>
```

Everything else is interpreted as a normal task and prints a plan. Use
`cairos run <task>` when you want CAIROS to execute after confirmation.

---

## 5. Planning without execution

Use `plan` to inspect what CAIROS would do:

```bash
cairos plan macke python projekt demo mit venv git pytest
```

The output contains:

```text
Summary
Source
Risk
Confirmation behavior
Steps
Verification checks
Notes
```

`Source` tells you whether the plan came from a deterministic template or AI.

Trust-focused review commands:

```bash
cairos --dry-run create python project demo
cairos preview create cpp header Player
cairos diff create cpp header Player
```

`--dry-run` never executes. `preview` lists affected paths. `diff` shows unified
diffs for file writes where possible.

---

## 6. Running tasks

Direct task usage prints the plan only:

```bash
cairos make folder docs
```

Use explicit run mode to execute:

```bash
cairos run make folder docs
```

For write actions, CAIROS asks:

```text
Type "yes" to execute:
```

Only exact `yes` continues.

For automated low/medium tests:

```bash
cairos run make folder docs --yes
```

Critical commands are still blocked.

---

## 7. Expand mode

`expand` prints a shell-equivalent command line from deterministic templates only:

```bash
cairos expand create python project demo with venv git
```

This is useful for shell integrations and for checking what CAIROS thinks the command should be.

If no local template matches, `expand` does not call AI.

---

## 8. Explain mode

Explain a shell command:

```bash
cairos explain git reset --soft HEAD~1
cairos explain rm -rf build
cairos explain find . -type f -size +100M -print
```

Output includes:

```text
Command
Risk
Meaning
Safety notes
Current context
```

Current deterministic explanations include common commands such as:

```text
git reset
git fetch
git merge
git rebase
git push
rm
find
chmod
chown
mkdir
touch
python -m venv
```

---

## 9. Safety behavior

Risk levels:

| Risk | Meaning |
|---|---|
| low | normal read-only or small local operation |
| medium | modifies files, recursive deletion of generated files, broad operation |
| high | dangerous but not always catastrophic, such as force push or curl-pipe-shell |
| critical | blocked by default |

Examples that are critical:

```bash
rm -rf /
rm -rf /*
sudo rm -rf ...
mkfs.ext4 /dev/sda
dd if=image.iso of=/dev/sda
:(){ :|:& };:
```

Check manually:

```bash
cairos check rm -rf /
cairos check git push --force
```

---

## 10. Local AI with Ollama

### Step 1: Install and run Ollama

Install Ollama using the official installer for your system. Then pull a model:

```bash
ollama pull llama3.1
```

Start the server if it is not already running:

```bash
ollama serve
```

### Step 2: Configure CAIROS

```bash
cairos config ai use-ollama llama3.1
```

Optional endpoint:

```bash
cairos config ai use-ollama llama3.1 --endpoint http://localhost:11434
```

### Step 3: Check status

```bash
cairos config ai status
cairos doctor
```

### Step 4: Use fallback AI

If a deterministic template cannot solve a task, CAIROS sends compact context and project rules to the local model.

CAIROS expects the model to return structured JSON. If the model returns invalid JSON, nothing is executed.

---

## 11. API-based AI setup

CAIROS supports OpenAI-compatible chat completions APIs.

### Step 1: Export your API key

Do **not** write secrets into the repository.

```bash
export OPENAI_API_KEY="your-key"
```

### Step 2: Configure provider

```bash
cairos config ai use-openai gpt-4.1-mini
```

Use a different environment variable:

```bash
export MY_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini --api-key-env MY_API_KEY
```

Use a custom compatible endpoint:

```bash
cairos config ai use-openai my-model --endpoint https://example.com/v1 --api-key-env MY_API_KEY
```

### Step 3: Check status

```bash
cairos config ai status
```

Status shows whether the key environment variable exists, but never prints the key.

---

## 12. Custom local AI command

You can plug in your own local planner command:

```bash
cairos config ai use-custom python3 ~/my_cairos_planner.py
```

Contract:

```text
stdin:  JSON containing system prompt, request, context and rules
stdout: JSON plan matching the CAIROS plan schema
```

The command should return JSON like:

```json
{
  "summary": "Create a file.",
  "risk": "low",
  "steps": [
    {
      "kind": "write_file",
      "path": "demo.txt",
      "content": "hello\n",
      "description": "Write demo file.",
      "changes_files": true,
      "risk": "low"
    }
  ],
  "notes": [],
  "verification": [
    {"kind": "file_exists", "target": "demo.txt"}
  ]
}
```

---

## 13. Disable AI

```bash
cairos config ai disable
```

Then CAIROS uses deterministic templates only.

---

## 14. Config file

Global config path:

```bash
cairos config path
```

Usually:

```text
~/.config/cairos/config.json
```

Show config:

```bash
cairos config show
```

Set any dotted key:

```bash
cairos config set behavior.max_context_files 120
cairos config set behavior.send_context_to_ai true
cairos config set ai.timeout_seconds 90
```

Main config fields:

```json
{
  "ai": {
    "provider": "none|ollama|openai|custom-command",
    "model": "model-name",
    "endpoint": "url",
    "api_key_env": "OPENAI_API_KEY",
    "custom_command": "...",
    "timeout_seconds": 60
  },
  "behavior": {
    "require_confirmation": true,
    "send_context_to_ai": true,
    "max_context_files": 80,
    "default_confirmation_phrase": "yes"
  }
}
```

---

## 15. Project rules

Rules teach CAIROS how projects should be structured.

Create local rules in the current project:

```bash
cairos rules init
```

Create global rules:

```bash
cairos rules init --global
```

Show merged active rules:

```bash
cairos rules show
```

Set rules:

```bash
cairos rules set cpp.namespace archmage
cairos rules set cpp.include_dir include
cairos rules set cpp.header_extension .hpp
cairos rules set git.main_branch main
```

Project-local rules live in:

```text
.cairos/rules.json
```

Global rules live in:

```text
~/.config/cairos/rules.json
```

Project-local rules override global rules.

---

## 16. Context sent to AI

CAIROS sends compact context, not the full repository.

Included:

```text
current working directory
shell
OS
project type
small file tree
git branch
git dirty state
git remotes
recent git log
CAIROS rules
user request
```

Excluded by default:

```text
.env files
private keys
.git internals
.venv
node_modules
build folders
binary files
large hidden caches
```

Show context:

```bash
cairos context
cairos context --json
```

---

## 17. Deterministic templates

Current offline templates include:

```text
create folder / mache ordner / macke ordner
create file / erstelle datei
create python project with venv/git/pytest/typer/rich
create C++ project with CMake
create C++ header with ifndef guards
create README
create .gitignore
setup venv
git init
git status
git fetch
safe branch preparation before push
find large files
clean __pycache__
run tests
```

The text matcher tolerates small typos and mixed German/English wording.

Examples:

```bash
cairos macke ordner docs
cairos mache python projekt crawler mit venv git pytest
cairos create cpp header file Player
```

---

## 18. Git workflow behavior

Request:

```bash
cairos finish current branch and prepare push to origin main
```

CAIROS does **not** merge or push immediately.

It creates a safe inspection workflow:

```text
git status --short
git branch --show-current
git fetch origin
git log --oneline --decorate --graph --max-count=12 --all
git log --oneline --left-right --cherry-pick HEAD...origin/main
```

Then you decide the next step.

Dangerous commands like these are high or critical:

```bash
git push --force
git reset --hard
git clean -fdx
```

---

## 19. Doctor command

```bash
cairos doctor
```

Shows:

```text
CAIROS version
Python version
executable path
config path
AI status
current context
```

Use it when debugging installation or AI configuration.

---

## 20. Testing

Run:

```bash
make test
```

This does:

```text
compile Python modules
run CAIROS testcases
write JSON results
write HTML test report
```

Reports:

```text
reports/results.json
reports/testreport.html
```

The test suite includes typo-tolerant templates, AI config commands, safety edge cases and dangerous-command classification.

---

## 21. History

History path:

```text
~/.local/state/cairos/history.jsonl
```

Commands:

```bash
cairos history
cairos history last
cairos history clear
```

History stores compact metadata only. It does not store file contents, command
output or raw API keys.

---

## 22. AI setup

Ollama:

```bash
cairos config ai use-ollama llama3.1
```

Gemini:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-1.5-flash
```

OpenAI-compatible:

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
```

Custom command:

```bash
cairos config ai use-custom python3 ~/my_cairos_planner.py
```

See `AI_SETUP.md` for details. CAIROS stores environment variable names, never
raw keys.

---

## 23. Dependency and install files

See:

```text
DEPENDENCIES.md
install_dependencies.sh
```

The runtime uses Python 3.10+ and the standard library only.
