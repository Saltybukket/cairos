# CAIROS Documentation

**CAIROS** means **Context-Aware Intelligent Runtime Operating Shell**.

CAIROS is not a replacement for zsh, bash or fish. It is a command-line assistant that runs inside your normal shell and helps you plan, explain and safely execute shell tasks.

---

# 1. Main idea

CAIROS receives a natural-language task:

```bash
cairos create python project testapp with venv git pytest
```

Then it follows this pipeline:

```text
User request
  -> collect compact context
  -> try deterministic regex/template planner
  -> if no template matches: try configured AI backend
  -> run safety checks
  -> print plan
  -> execute only after confirmation
  -> verify result
  -> summarize
```

The AI is optional. CAIROS can already solve many simple tasks without AI.

---

# 2. Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Check:

```bash
cairos --version
cairos --help
```

Run the test suite:

```bash
make test
```

The HTML report is generated at:

```text
reports/testreport.html
```

---

# 3. Natural-language usage

The intended default usage is:

```bash
cairos <task>
```

Examples:

```bash
cairos create python project crawler with venv git pytest
cairos create cpp project engine with cmake
cairos create cpp header file Player
cairos create folder docs
cairos find large files
cairos clean pycache
cairos finish current branch and prepare push to origin main
```

When a task changes files, CAIROS prints the plan and asks for confirmation.

Default confirmation phrase:

```text
yes
```

For high-risk actions, CAIROS can require a stronger confirmation phrase.

---

# 4. Reserved commands

Some commands have special meaning and are not treated as free natural language.

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
```

---

# 5. `cairos plan`

Creates a plan without executing it.

```bash
cairos plan create python project crawler with venv git pytest
```

Output includes:

```text
Summary
Source
Risk
Confirmation behavior
Steps
Verification
Notes
```

This is the safest way to inspect what CAIROS would do.

---

# 6. `cairos expand`

Prints a shell-equivalent command line.

```bash
cairos expand create python project crawler with venv git
```

This mode uses deterministic templates only. It does not call AI.

If no deterministic template matches, CAIROS exits with code `1` and writes an error to stderr.

---

# 7. `cairos run`

Creates a plan and executes it.

```bash
cairos run create folder docs
```

CAIROS prints the plan and asks:

```text
Type "yes" to execute:
```

Only exact `yes` continues.

For low/medium automation tests you can use:

```bash
cairos run create folder docs --yes
```

Use `--yes` carefully. Critical commands are still blocked.

---

# 8. Direct free task execution

This also works:

```bash
cairos create folder docs
```

This behaves like `cairos run <task>` and asks for confirmation before changing files.

---

# 9. `cairos explain`

Explains a shell command and shows risk information.

```bash
cairos explain git reset --soft HEAD~1
cairos explain rm -rf build
cairos explain find . -type f -size +100M -print
```

The output includes:

```text
Command
Risk
Meaning
Safety notes
Current context
```

Currently deterministic explanations exist for common commands like:

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

# 10. `cairos check`

Checks a shell command for dangerous patterns.

```bash
cairos check rm -rf /
cairos check git clean -fdx
cairos check curl https://example.com/install.sh | bash
```

Risk levels:

```text
low       no dangerous pattern detected
medium    potentially broad file operation
high      dangerous but not always catastrophic
critical  blocked by default
```

Examples of critical patterns:

```text
rm -rf /
rm -rf /*
sudo rm -rf ...
mkfs...
dd ... of=/dev/...
fork bomb
```

Examples of high-risk patterns:

```text
git push --force
git reset --hard
git clean -fdx
curl ... | bash
wget ... | sh
chmod -R 777 /
```

---

# 11. Context system

CAIROS collects compact context so templates and AI can understand the current situation.

```bash
cairos context
cairos context --json
```

Context includes:

```text
current working directory
current shell
operating system
project type
git branch
git dirty state
git remotes
recent git log
compact file tree
```

CAIROS intentionally excludes common sensitive or huge directories:

```text
.git
.venv
node_modules
__pycache__
.env files
private key names
build/dist folders
```

---

# 12. Config system

Global config path:

```text
~/.config/cairos/config.json
```

Show config:

```bash
cairos config show
```

AI status:

```bash
cairos config ai status
```

Set AI provider:

```bash
cairos config ai set-provider none
cairos config ai set-provider ollama
cairos config ai set-provider openai
cairos config ai set-provider custom-command
```

Set model:

```bash
cairos config ai set-model llama3.1
cairos config ai set-model gpt-4.1-mini
```

Set endpoint:

```bash
cairos config ai set-endpoint http://localhost:11434
cairos config ai set-endpoint https://api.openai.com/v1
```

Set API key environment variable name:

```bash
cairos config ai set-api-key-env OPENAI_API_KEY
```

Set custom command backend:

```bash
cairos config ai set-custom-command /path/to/local-planner
```

Generic config setting:

```bash
cairos config set behavior.require_confirmation true
```

---

# 13. AI backend behavior

If a deterministic template matches, CAIROS does not need AI.

If no template matches and no AI is configured, CAIROS prints:

```text
No deterministic template matched this request.
No AI backend is configured.
```

If AI is configured, CAIROS sends a compact JSON payload containing:

```text
system instructions
user request
safe context summary
project file tree
rules
```

The AI must return structured JSON, not prose.

Supported step kinds:

```text
command
mkdir
write_file
append_file
```

CAIROS validates the AI plan, runs safety checks, prints the plan, and asks for confirmation before execution.

---

# 14. Rules system

Global rules path:

```text
~/.config/cairos/rules.json
```

Project-local rules path:

```text
.cairos/rules.json
```

Project rules override global rules.

Initialize local rules:

```bash
cairos rules init
```

Show merged rules:

```bash
cairos rules show
```

Set a rule:

```bash
cairos rules set cpp.header_extension .hpp
cairos rules set cpp.namespace archmage
cairos rules set git.main_branch main
```

Example rules:

```json
{
  "cpp": {
    "header_style": "ifndef",
    "header_extension": ".hpp",
    "include_dir": "include",
    "source_dir": "src",
    "namespace": ""
  },
  "git": {
    "main_branch": "main",
    "remote": "origin",
    "force_push_allowed": false
  }
}
```

---

# 15. Deterministic templates

CAIROS currently supports deterministic templates for:

```text
create python project
create cpp project
create cpp header file
setup venv
git init
create folder
create file
find large files
clean pycache
finish current branch / prepare push workflow
```

These templates are fast, offline and safer than AI-generated shell commands.

---

# 16. Git workflow assistant

Example:

```bash
cairos finish current branch and prepare push to origin main
```

CAIROS intentionally does not immediately push.

It plans read-only safe steps:

```bash
git status --short
git branch --show-current
git fetch origin
git log --oneline --decorate --graph --max-count=10 --all
```

Then the user can decide whether to merge, rebase, commit or push.

Future versions can add an interactive multi-stage workflow:

```text
fetch
inspect
ask before merge/rebase
run tests
ask before push
verify remote log
summarize
```

---

# 17. C++ helper behavior

Example:

```bash
cairos create cpp header file Player
```

Creates:

```text
include/Player.hpp
```

With:

```cpp
#ifndef PLAYER_HPP
#define PLAYER_HPP

class Player {
public:
    Player();
    Player(const Player& other);
    Player(Player&& other) noexcept;
    Player& operator=(const Player& other);
    Player& operator=(Player&& other) noexcept;
    ~Player();

private:
};

#endif // PLAYER_HPP
```

If `cpp.namespace` is set, CAIROS wraps the class in that namespace.

---

# 18. Python helper behavior

Example:

```bash
cairos create python project crawler with venv git pytest
```

Creates a modern project skeleton:

```text
crawler/
├── .gitignore
├── README.md
├── pyproject.toml
├── crawler/
│   └── __init__.py
└── tests/
    └── test_basic.py
```

If `venv` is requested, it also creates `.venv`.

If `git` is requested, it runs `git init` inside the project.

---

# 19. `cairos doctor`

Prints useful diagnostic information:

```bash
cairos doctor
```

Includes:

```text
CAIROS version
config path
AI backend status
current context
```

---

# 20. Development and tests

Run:

```bash
make test
```

The test runner executes JSON-defined CLI testcases and writes:

```text
reports/results.json
reports/testreport.html
```

The HTML report is intentionally similar to university-style public/private testcase reports.

---

# 21. Exit codes

Typical exit codes:

```text
0    success
1    general failure or unknown task
2    critical command blocked
3    verification failed
130  aborted by user
```

---

# 22. Safety principle

CAIROS should be:

```text
fast when deterministic
smart when AI is configured
safe before execution
transparent before modifying files
context-aware before planning
```

The AI is not the authority. CAIROS safety checks and user confirmation are the authority.
