# CAIROS Usage

Direct tasks plan only:

```bash
cairos create python project demo with venv
```

Execute explicitly:

```bash
cairos run create folder docs --yes
```

Review tools:

```bash
cairos plan create cpp header Player
cairos expand create cpp header Player
cairos preview create bash script branch_info that prints current git branch and folder
cairos diff create bash script branch_info that prints current git branch and folder
```

Compound project/file requests:

```bash
cairos plan create a folder named new_cpp_project with one file named main_cpp.cpp with a class called TestSubject
cairos plan create cpp mini project new_cpp_project with class TestSubject and main
```

For C++, prefer `.hpp` files for declarations and include guards, and `.cpp`
files for implementations.

`check` is dual-use. Shell-looking input runs safety mode:

```bash
cairos check rm -rf /
```

Natural language routes to planning:

```bash
cairos check if repo is ready to commit
```

Use `cairos -- <task>` or `cairos ask <task>` when a task starts with a reserved
word and you want natural-language planning.
