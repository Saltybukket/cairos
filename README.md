# CAIROS

**CAIROS — Context-Aware Intelligent Runtime Operating Shell**

CAIROS is a context-aware AI-assisted command layer for your terminal. It first tries fast deterministic templates and only falls back to an optional AI backend when it cannot solve a task locally.

```bash
cairos create python project demo with venv git pytest
cairos create cpp header file Player
cairos explain git reset --soft HEAD~1
cairos check rm -rf /
cairos config ai status
```

See [`DOCUMENTATION.md`](DOCUMENTATION.md) for full usage, commands, settings and behavior.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cairos --version
make test
```

## Current status

This is an early development version. It already includes deterministic planners, safety checks, rules/config files, AI backend configuration stubs, structured execution with confirmation, and a HTML test report generator.
