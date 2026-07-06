# CAIROS Milestones

## Done in this version

- Free-text CLI usage: `cairos <task>`
- Reserved commands: `plan`, `expand`, `run`, `check`, `explain`, `context`, `config`, `rules`, `doctor`
- Structured `Plan`, `CommandStep`, and `VerificationStep` models
- Deterministic templates for Python, C++, folders, files, pycache cleanup and git preparation
- Safety levels and critical blocking
- Confirmation before write operations
- Config system for future AI backends
- Rules system for project conventions
- Context collector for project/git/shell state
- AI backend interface for Ollama, OpenAI-compatible APIs and custom commands
- HTML testcase report generator
- Deterministic Bash script generation
- Gemini model listing and `config ai test`
- Natural-language `check ...` routing for Git inspection
- Git add/commit/push safety upgrades
- Preview, diff and safe history

## Next milestones

1. Interactive multi-stage Git workflow with merge/rebase/push confirmation.
2. Richer diff preview before modifying existing files.
3. Better shell quoting and command AST representation.
4. More history filters and search.
5. `cairos undo last` for CAIROS-created files.
6. Rich terminal output with colors and panels.
7. More deterministic templates for Node, Rust, CMake libraries and Makefiles.
8. AI explain fallback for unknown shell commands.
9. Secret scanner before AI context is sent.
10. Shell integrations for zsh/bash/fish widgets.
