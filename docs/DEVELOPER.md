# Developing CAIROS

This file explains contributor setup, checks, architecture, and release steps.

Main modules:

- `cairos/cli.py`: command routing.
- `cairos/templates.py`: deterministic planning.
- `cairos/safety.py`: risk scanning.
- `cairos/context.py`: compact project context.
- `cairos/ai/`: AI backends and validation.
- `cairos/preview.py`: preview and diff output.
- `cairos/history.py`: safe history.

Run checks:

```bash
make compile
make test
make secret-check
make check
```

Network AI tests are optional:

```bash
make test-ai
```

Use match debugging for template work:

```bash
cairos plan --debug-match create a small bash script that prints current folder
cairos plan --debug-route change into the directory oop ss26 at least its named something like that
```

Templates should only win when confidence is high. Broad requests such as
release preparation, fuzzy navigation, or "fix everything" workflows should
step back to AI fallback or a clear no-match. Keep routing heuristics in
`cairos/router.py` and target extraction helpers in `cairos/shell_utils.py`.

## Release

Install build tooling only when preparing a release:

```bash
python -m pip install build twine
make check
python -m build
twine check dist/*
twine upload dist/*
```

Release checklist:

- Bump version.
- Update changelog.
- Run `make secret-check`.
- Run `make check`.
- Tag the release.
