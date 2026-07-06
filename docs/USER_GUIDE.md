# CAIROS User Guide

CAIROS is a command-line assistant that runs inside your normal terminal. It is
useful without AI, and can use AI as a fallback when deterministic templates do
not cover a request.

Pipeline:

```text
request -> context -> deterministic template -> optional AI fallback -> safety scan -> plan -> explicit execution
```

## Commands

```bash
cairos <task in natural language>
cairos plan <task>
cairos expand <task>
cairos run <task> [--yes]
cairos --dry-run <task>
cairos preview <task>
cairos diff <task>
cairos explain <shell command>
cairos check <shell command | natural language task>
cairos context [--json]
cairos config ...
cairos rules ...
cairos quicksetup
cairos setup
cairos install-info
cairos doctor
cairos templates [python|cpp|git|ai]
cairos shell install zsh
cairos shell install powershell
cairos history [last|clear]
```

Direct task usage prints a plan:

```bash
cairos create folder docs
```

Execution is explicit:

```bash
cairos run create folder docs
```

For write actions, CAIROS asks for confirmation unless `--yes` is supplied.
Critical commands remain blocked.

## Planning and Review

Use `plan` to inspect the chosen source, risk, steps, verification checks, and
notes:

```bash
cairos plan create python project crawler with venv git pytest
```

Use `expand` when you want shell-equivalent deterministic output only:

```bash
cairos expand create python project crawler with venv git
```

Use preview and diff before writing files:

```bash
cairos preview create cpp header Player
cairos diff create cpp header Player
```

## Templates

List common deterministic requests:

```bash
cairos templates
cairos templates python
cairos templates cpp
cairos templates git
cairos templates ai
```

Examples:

```bash
cairos create python project demo with venv git pytest
cairos create cpp header Player
cairos create cpp project engine with cmake
cairos create bash script branch_info that prints current git branch and folder
cairos check if repo is ready to commit
```

## Compound Requests

CAIROS can handle small multi-target requests when a deterministic template
covers the full intent:

```bash
cairos plan create a folder named new_cpp_project with one file named main_cpp.cpp with a main function and a class called TestSubject
```

It can also create small project structures:

```bash
cairos plan create cpp mini project new_cpp_project with class TestSubject and main
```

The mini C++ project template creates a header, implementation file, main file,
and `CMakeLists.txt`.

Simple one-target templates step back when a request includes multiple creation
targets such as folder plus file plus content/class/function. That lets a
compound template or AI fallback handle the complete request instead of
misreading a word such as `named` as a filename.

## C++ Best Practice

Use `.hpp` or `.h` files for declarations and include guards:

```cpp
#ifndef TESTSUBJECT_HPP
#define TESTSUBJECT_HPP

class TestSubject {
public:
    TestSubject() = default;
};

#endif
```

Use `.cpp` files for implementations and `main`.

Header guards in `.cpp` files are unusual. CAIROS can satisfy that explicit
request when asked, but the recommended project layout keeps guards in headers.

## Safety

Risk levels:

| Risk | Meaning |
|---|---|
| low | read-only or small local operation |
| medium | writes files or performs broad but normal project operations |
| high | potentially dangerous, such as force push or curl-pipe-shell |
| critical | blocked by default |

Check shell commands directly:

```bash
cairos check rm -rf /
cairos check git push --force
```

Natural-language `check` requests route to planning:

```bash
cairos check if repo is ready to push
```

## Configuration

Show the active config:

```bash
cairos config show
```

Print the config path:

```bash
cairos config path
```

Set values:

```bash
cairos config set behavior.max_context_files 120
cairos config set behavior.send_context_to_ai true
cairos config set ai.timeout_seconds 90
```

Global config on Linux/macOS/WSL:

```text
~/.config/cairos/config.json
```

Global config on Windows:

```text
%APPDATA%\cairos\config.json
```

History on Linux/macOS/WSL:

```text
~/.local/state/cairos/history.jsonl
```

History on Windows:

```text
%LOCALAPPDATA%\cairos\history.jsonl
```

## Project Rules

Project-local rules are optional and live in:

```text
.cairos/rules.json
```

Create them:

```bash
cairos rules init
```

Set common C++ preferences:

```bash
cairos rules set cpp.namespace archmage
cairos rules set cpp.include_dir include
cairos rules set cpp.header_extension .hpp
```

Global rules live beside the global config:

```bash
cairos rules init --global
```

## AI Backends

Disable AI:

```bash
cairos config ai disable
```

Use Ollama:

```bash
ollama pull llama3.1
cairos config ai use-ollama llama3.1
```

Use Gemini:

```bash
export GEMINI_API_KEY="your-key"
cairos config ai use-gemini gemini-2.5-flash
```

Use OpenAI-compatible APIs:

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
```

Check status:

```bash
cairos config ai status
cairos config ai test
```

CAIROS reports whether an API key environment variable exists, but never prints
the key value.

## Shell Helpers

Shell helper commands are conservative:

```bash
cairos shell install zsh
cairos shell install powershell
```

They print optional snippets and do not silently modify shell profile files.
