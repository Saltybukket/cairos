# CAIROS Template Library

CAIROS prefers deterministic templates before AI.

## Files and Folders

```bash
cairos make folder docs
cairos create directory src/components
cairos create file README.md
cairos create nested folder src/core/utils
cairos list large files
cairos clean pycache
```

## Python

```bash
cairos create python project crawler with venv git pytest
cairos setup venv
cairos create requirements file
cairos create pyproject
cairos add pytest
cairos add typer
cairos add rich
```

## C and C++

```bash
cairos create cpp project engine
cairos create cpp header Player
cairos create source file Player
cairos create cmake file
```

Rules can add namespaces:

```bash
cairos rules set cpp.namespace archmage
cairos create cpp header Player
```

## Git

```bash
cairos git status summary
cairos fetch origin
cairos show recent commits
cairos undo last commit keep changes
cairos unstage all
cairos finish current branch for origin main
```

The finish workflow inspects status and remote relationships. It does not merge
or push automatically.

## Node and Rust

```bash
cairos create node project app
cairos create vite project app
cairos npm install
cairos npm test
cairos create rust project tool
cairos cargo test
```

## Build and Test

```bash
cairos run tests
cairos build project
cairos clean build
cairos create makefile
```
