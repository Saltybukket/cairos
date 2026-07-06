# CAIROS Release Guide

This guide covers the current GitHub-first release flow and the future PyPI
release flow.

Package/distribution name: `cairos-shell`  
Terminal command: `cairos`  
GitHub repo: `Saltybukket/cairos`

## Before Release

```bash
make check
make test
make secret-check
python -m compileall -q cairos scripts
git status --short
```

## Build Package Locally

```bash
python -m pip install build twine
python -m build
twine check dist/*
```

## GitHub Release

```bash
git tag v0.4.0a1
git push origin v0.4.0a1
```

## Install From GitHub Tag

```bash
pipx install git+https://github.com/Saltybukket/cairos.git@v0.4.0a1
```

## Future PyPI Release

There is no PyPI release yet. After the PyPI account/project exists and the
package name is reserved, publish with:

```bash
twine upload dist/*
```

Future PyPI users will install with:

```bash
pipx install cairos-shell
```
