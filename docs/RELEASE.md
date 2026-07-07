# CAIROS Release Guide

Package/distribution name: `cairos-shell`
Terminal command: `cairos`
GitHub repo: `Saltybukket/cairos`
Tag convention: `v0.5.0a3`

CAIROS publishes to PyPI through GitHub Actions Trusted Publishing. Do not use
long-lived PyPI API tokens.

## First-Time PyPI Setup

Create/configure the PyPI Trusted Publisher manually with these exact values:

```text
PyPI project name: cairos-shell
Owner: Saltybukket
Repository name: cairos
Workflow name: publish.yml
Environment name: pypi
```

Notes:

- The PyPI project name is `cairos-shell`.
- The terminal command remains `cairos`.
- The workflow file is `.github/workflows/publish.yml`.
- The GitHub Actions environment is `pypi`.
- No PyPI API token is needed.

## Pre-Release Checks

```bash
git status --short
cairos --version
python -m compileall -q cairos scripts tests
make compile
make test
make check
make secret-check
make docs-check
make release-check
```

`make release-check` cleans old build artifacts, builds sdist/wheel, and runs
`twine check`.

## Local Build Verification

```bash
rm -rf dist build *.egg-info
python -m build
python -m twine check dist/*
python -m tarfile -l dist/*.tar.gz | head -100
python -m zipfile -l dist/*.whl | head -100
python -m zipfile -l dist/*.whl | grep 'cairos/gui/templates'
python -m zipfile -l dist/*.whl | grep 'cairos/gui/static'
```

The wheel must include GUI templates and static assets.

## Release Steps

After all checks pass and the PyPI Trusted Publisher exists:

```bash
git status --short
git tag v0.5.0a3
git push origin main
git push origin v0.5.0a3
```

Then create GitHub Release `v0.5.0a3`. Publishing runs automatically from the
`Publish Python package` workflow.

Check:

```text
https://pypi.org/project/cairos-shell/
```

## After Publish Verification

```bash
pipx install cairos-shell
cairos --version
cairos quicksetup
cairos gui --check
```

GUI dependencies after PyPI:

```bash
pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart
cairos gui --check
```

If extras are verified in the published package:

```bash
pipx install "cairos-shell[gui]"
```

## Current Pre-PyPI Install

Until the first PyPI release is published, use the GitHub install:

```bash
pipx install git+https://github.com/Saltybukket/cairos.git
```

Config, history, AI profiles, environment variable names, and project rules live
outside the package environment and are preserved across package upgrades.
