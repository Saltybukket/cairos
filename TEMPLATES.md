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
cairos create bash script branch_info that prints current git branch and folder
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
cairos create cpp mini project new_cpp_project with class TestSubject and main
cairos create cpp header Player
cairos create source file Player
cairos create cmake file
cairos create a folder named new_cpp_project with one file named main_cpp.cpp with a class called TestSubject
```

Rules can add namespaces:

```bash
cairos rules set cpp.namespace archmage
cairos create cpp header Player
```

CAIROS can handle small compound C++ requests when the folder and file are
explicitly named. For production C++, prefer declarations and include guards in
`.hpp`/`.h` headers and implementations in `.cpp` files. If you ask for header
guards inside a `.cpp`, CAIROS will do it but will warn that this is unusual.

## Git

```bash
cairos git status summary
cairos fetch origin
cairos show recent commits
cairos undo last commit keep changes
cairos unstage all
cairos finish current branch for origin main
cairos check if repo is ready to commit
cairos check if repo is ready to push
cairos git summary
cairos summarize commit log
```

The finish workflow inspects status and remote relationships. It does not merge
or push automatically.

Git inspection templates are read-only except for `git fetch origin`, which only
updates remote-tracking references.

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
