"""Deterministic task templates for CAIROS.

The template layer is the fast offline brain of CAIROS.  It handles common shell
and project tasks without AI: creating folders, scaffolding Python/C++ projects,
creating header files, checking git state, cleaning generated caches, and more.

When a task is not recognized here, ``planner.py`` may optionally delegate it to
an AI backend.  Adding templates is the best way to make CAIROS faster and more
reliable while reducing AI usage.
"""

from __future__ import annotations

import re
from pathlib import Path
import shlex

from .models import CommandStep, Plan, VerificationStep
from .rules import load_rules
from .text import candidate_words, has_all, has_concept, tokenize

PROJECT_NAME_RE = r"[a-zA-Z][a-zA-Z0-9_-]*"
CLASS_NAME_RE = r"[A-Z][a-zA-Z0-9_]*"
PATH_RE = r"[a-zA-Z0-9_./-]+"
UNSAFE_NAME_RE = re.compile(r"[;&|><`$(){}\n\r]")
NAMED_VALUE_RE = r"\"([^\"]+)\"|'([^']+)'|([a-zA-Z][a-zA-Z0-9_./-]*)"


def _extract_name(text: str, default: str = "demo") -> str:
    """Extract a likely project/folder/file name from free text."""
    named = _extract_named_value(text, "any")
    if named:
        return named
    patterns = [
        rf"(?:project|projekt|folder|directory|ordner|repo|repository)\s+({PROJECT_NAME_RE})",
        rf"(?:called|named|namens)\s+({PROJECT_NAME_RE})",
        rf"(?:python|cpp|c\+\+|cmake)\s+(?:project|projekt)\s+({PROJECT_NAME_RE})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    candidates = candidate_words(text)
    return candidates[-1] if candidates else default


def _first_group(match: re.Match[str]) -> str:
    """Return the first non-empty capture group from a regex match."""
    for value in match.groups():
        if value:
            return value
    return ""


def _extract_named_value(text: str, label: str) -> str | None:
    """Extract values from forms such as ``file named "main.cpp"``."""
    label_pattern = {
        "folder": r"(?:folder|directory|dir|ordner|project folder)",
        "file": r"(?:file|datei|source file)",
        "class": r"(?:class|klasse)",
        "any": r"",
    }.get(label, re.escape(label))
    if label == "any":
        patterns = [rf"\b(?:named|called|namens)\s+(?:{NAMED_VALUE_RE})"]
    else:
        patterns = [
            rf"\b{label_pattern}\b(?:\s+in\s+this\s+directory)?\s+(?:named|called|namens)\s+(?:{NAMED_VALUE_RE})",
            rf"\b(?:with\s+one\s+)?{label_pattern}\s+(?:named|called|namens)\s+(?:{NAMED_VALUE_RE})",
        ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _first_group(match)
    return None


def _safe_rel_path(value: str) -> str | None:
    """Return a safe relative path/name, or ``None`` when unsafe."""
    if not value or UNSAFE_NAME_RE.search(value):
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return value


def _unsafe_path_plan(value: str) -> Plan:
    return Plan(
        summary=f"Refuse unsafe path {value!r}.",
        steps=[],
        risk="high",
        notes=["Path names must be relative and must not contain shell metacharacters or '..'."],
        source="template:path-safety",
        requires_confirmation=False,
    )


def _extract_path_after_keywords(text: str, keywords: list[str], default: str) -> str:
    """Extract a path appearing after one of several marker words."""
    for keyword in keywords:
        match = re.search(rf"\b{re.escape(keyword)}\s+({PATH_RE})", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    candidates = [word for word in candidate_words(text) if "/" in word or "." in word]
    return candidates[-1] if candidates else default


def _extract_class_name(text: str, default: str = "Demo") -> str:
    """Extract a likely C++ class name from a request."""
    named_class = _extract_named_value(text, "class")
    if named_class:
        return named_class[:1].upper() + named_class[1:]
    explicit_patterns = [
        rf"(?:class|klasse)\s+({CLASS_NAME_RE})",
        rf"(?:header|file|datei)\s+({CLASS_NAME_RE})",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            name = match.group(1)
            if name.lower() not in {"cpp", "c", "hpp", "header", "file", "datei", "class", "klasse"}:
                return name[:1].upper() + name[1:]
    candidates = candidate_words(text)
    if candidates:
        name = candidates[-1]
        return name[:1].upper() + name[1:]
    return default


def _header_guard(class_name: str, extension: str) -> str:
    raw = f"{class_name}{extension}".upper()
    return re.sub(r"[^A-Z0-9]", "_", raw)


def _cpp_header_content(class_name: str, namespace: str = "", extension: str = ".hpp") -> str:
    """Generate a C++ class header using ifndef guards."""
    guard = _header_guard(class_name, extension)
    open_namespace = f"namespace {namespace} {{\n\n" if namespace else ""
    close_namespace = f"\n}} // namespace {namespace}\n" if namespace else ""
    return f"""#ifndef {guard}
#define {guard}

{open_namespace}class {class_name} {{
public:
    {class_name}();
    {class_name}(const {class_name}& other);
    {class_name}({class_name}&& other) noexcept;
    {class_name}& operator=(const {class_name}& other);
    {class_name}& operator=({class_name}&& other) noexcept;
    ~{class_name}();

private:
}};{close_namespace}
#endif // {guard}
"""


def _python_project_plan(request: str) -> Plan:
    """Create a modern minimal Python package project."""
    name = _extract_name(request)
    package = name.replace("-", "_")
    request_l = request.lower()
    use_pytest = "pytest" in request_l or has_concept(tokenize(request), "test")
    use_typer = "typer" in request_l
    use_rich = "rich" in request_l
    deps = []
    if use_typer:
        deps.append('"typer>=0.12"')
    if use_rich:
        deps.append('"rich>=13"')
    deps_text = "dependencies = [" + ", ".join(deps) + "]\n" if deps else "dependencies = []\n"
    pyproject = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.10"
{deps_text}

[tool.setuptools.packages.find]
where = ["."]
include = ["{package}*"]
"""
    steps = [
        CommandStep(kind="mkdir", path=name, description="Create the project root directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/{package}", description="Create the Python package directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/tests", description="Create the test directory.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/{package}/__init__.py", content='__version__ = "0.1.0"\n', description="Create package initializer.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/.gitignore", content=".venv/\nvenv/\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\nbuild/\ndist/\n", description="Create Python .gitignore.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/pyproject.toml", content=pyproject, description="Create pyproject.toml.", changes_files=True),
    ]
    if use_pytest:
        steps.append(CommandStep(kind="write_file", path=f"{name}/tests/test_basic.py", content="def test_basic():\n    assert True\n", description="Create a basic pytest test.", changes_files=True))
    if has_concept(tokenize(request), "venv"):
        steps.append(CommandStep(kind="command", command=f"cd {name} && python3 -m venv .venv", description="Create a Python virtual environment.", changes_files=True))
    if has_concept(tokenize(request), "git"):
        steps.append(CommandStep(kind="command", command=f"cd {name} && git init", description="Initialize git repository.", changes_files=True))
    return Plan(
        summary=f"Create a Python project named {name}.",
        steps=steps,
        risk="low",
        notes=["Activate the venv with: source .venv/bin/activate" if has_concept(tokenize(request), "venv") else "No venv requested."],
        verification=[VerificationStep(kind="dir_exists", target=name), VerificationStep(kind="file_exists", target=f"{name}/pyproject.toml")],
        source="template:python-project",
    )


def _cpp_project_plan(request: str) -> Plan:
    """Create a minimal CMake-based C++ project."""
    rules = load_rules()["cpp"]
    name = _extract_name(request)
    include_dir = rules.get("include_dir", "include")
    source_dir = rules.get("source_dir", "src")
    test_dir = rules.get("test_dir", "tests")
    standard = rules.get("standard", "17")
    cmake = f"""cmake_minimum_required(VERSION 3.16)
project({name})

set(CMAKE_CXX_STANDARD {standard})
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable({name} {source_dir}/main.cpp)
target_include_directories({name} PRIVATE {include_dir})
"""
    main_cpp = "#include <iostream>\n\nint main() {\n    std::cout << \"Hello from CAIROS!\" << std::endl;\n    return 0;\n}\n"
    return Plan(
        summary=f"Create a C++ project named {name}.",
        steps=[
            CommandStep(kind="mkdir", path=f"{name}/{include_dir}", description="Create include directory.", changes_files=True),
            CommandStep(kind="mkdir", path=f"{name}/{source_dir}", description="Create source directory.", changes_files=True),
            CommandStep(kind="mkdir", path=f"{name}/{test_dir}", description="Create test directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/CMakeLists.txt", content=cmake, description="Create CMake configuration.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/{source_dir}/main.cpp", content=main_cpp, description="Create main.cpp.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=name), VerificationStep(kind="file_exists", target=f"{name}/CMakeLists.txt")],
        source="template:cpp-project",
    )


def _cpp_compound_content(filename: str, class_name: str) -> str:
    guard = re.sub(r"[^A-Z0-9]", "_", f"{Path(filename).stem}_hpp".upper())
    return f"""#ifndef {guard}
#define {guard}

#include <iostream>

class {class_name} {{
public:
    {class_name}() = default;
}};

int main() {{
    {class_name} subject;
    std::cout << "Hello from {class_name}" << std::endl;
    return 0;
}}

#endif // {guard}
"""


def _cpp_compound_plan(request: str) -> Plan:
    """Create a small C++ folder with one requested source file and class."""
    folder = _extract_named_value(request, "folder") or _extract_named_value(request, "project") or _extract_name(request, "new_cpp_project")
    filename = _extract_named_value(request, "file") or "main.cpp"
    class_name = _extract_class_name(request, "TestSubject")
    safe_folder = _safe_rel_path(folder)
    safe_file = _safe_rel_path(filename)
    if safe_folder is None:
        return _unsafe_path_plan(folder)
    if safe_file is None:
        return _unsafe_path_plan(filename)
    path = str(Path(safe_folder) / safe_file)
    return Plan(
        summary=f"Create C++ folder {safe_folder} with {safe_file} containing a main function and {class_name} class.",
        steps=[
            CommandStep(kind="mkdir", path=safe_folder, description=f"Create folder {safe_folder}.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=_cpp_compound_content(safe_file, class_name), description=f"Write {safe_file} with {class_name} and int main().", changes_files=True),
        ],
        risk="low",
        notes=["Header guards are unusual in .cpp files; normally they belong in .hpp/.h files."],
        verification=[VerificationStep(kind="dir_exists", target=safe_folder), VerificationStep(kind="file_exists", target=path)],
        source="template:cpp_compound",
    )


def _folder_file_compound_plan(request: str) -> Plan:
    """Create a folder with a single requested file when no language template applies."""
    folder = _extract_named_value(request, "folder") or _extract_name(request, "demo")
    filename = _extract_named_value(request, "file") or "main.txt"
    safe_folder = _safe_rel_path(folder)
    safe_file = _safe_rel_path(filename)
    if safe_folder is None:
        return _unsafe_path_plan(folder)
    if safe_file is None:
        return _unsafe_path_plan(filename)
    path = str(Path(safe_folder) / safe_file)
    content = ""
    if filename.endswith(".py"):
        content = "def main():\n    pass\n\n\nif __name__ == \"__main__\":\n    main()\n"
    return Plan(
        summary=f"Create folder {safe_folder} with file {safe_file}.",
        steps=[
            CommandStep(kind="mkdir", path=safe_folder, description=f"Create folder {safe_folder}.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=content, description=f"Write {path}.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=safe_folder), VerificationStep(kind="file_exists", target=path)],
        source="template:folder-file-compound",
    )


def _cpp_mini_project_plan(request: str) -> Plan:
    """Create a tiny multi-file C++ project with header, source, main and CMake."""
    name = _extract_name(request, "new_cpp_project")
    class_name = _extract_class_name(request, "TestSubject")
    safe_name = _safe_rel_path(name)
    if safe_name is None:
        return _unsafe_path_plan(name)
    guard = _header_guard(class_name, ".hpp")
    header = f"""#ifndef {guard}
#define {guard}

class {class_name} {{
public:
    {class_name}();
}};

#endif // {guard}
"""
    source = f'#include "{class_name}.hpp"\n\n{class_name}::{class_name}() = default;\n'
    main = f"""#include "{class_name}.hpp"

int main() {{
    {class_name} subject;
    return 0;
}}
"""
    cmake = f"""cmake_minimum_required(VERSION 3.16)
project({safe_name})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable({safe_name} src/main.cpp src/{class_name}.cpp)
target_include_directories({safe_name} PRIVATE include)
"""
    return Plan(
        summary=f"Create C++ mini project {safe_name} with class {class_name} and main.",
        steps=[
            CommandStep(kind="mkdir", path=f"{safe_name}/include", description="Create include directory.", changes_files=True),
            CommandStep(kind="mkdir", path=f"{safe_name}/src", description="Create source directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{safe_name}/include/{class_name}.hpp", content=header, description="Write class header.", changes_files=True),
            CommandStep(kind="write_file", path=f"{safe_name}/src/{class_name}.cpp", content=source, description="Write class implementation.", changes_files=True),
            CommandStep(kind="write_file", path=f"{safe_name}/src/main.cpp", content=main, description="Write main function.", changes_files=True),
            CommandStep(kind="write_file", path=f"{safe_name}/CMakeLists.txt", content=cmake, description="Write CMakeLists.txt.", changes_files=True),
        ],
        risk="low",
        notes=["C++ best practice: put declarations and header guards in .hpp/.h files, and implementations in .cpp files."],
        verification=[VerificationStep(kind="file_exists", target=f"{safe_name}/CMakeLists.txt")],
        source="template:cpp-mini-project",
    )


def _cpp_header_plan(request: str) -> Plan:
    """Create a C++ header file using project rules."""
    rules = load_rules()["cpp"]
    class_name = _extract_class_name(request)
    include_dir = rules.get("include_dir", "include")
    extension = rules.get("header_extension", ".hpp")
    namespace = rules.get("namespace", "")
    path = _extract_path_after_keywords(request, ["at", "in", "into", "nach", "unter"], f"{include_dir}/{class_name}{extension}")
    if not Path(path).suffix:
        path = str(Path(path) / f"{class_name}{extension}")
    return Plan(
        summary=f"Create C++ header for class {class_name}.",
        steps=[
            CommandStep(kind="mkdir", path=str(Path(path).parent), description="Create header parent directory.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=_cpp_header_content(class_name, namespace, extension), description=f"Write ifndef header guard and class {class_name}.", changes_files=True),
        ],
        risk="low",
        notes=["Header style comes from CAIROS rules: cpp.header_style=ifndef."],
        verification=[VerificationStep(kind="file_exists", target=path)],
        source="template:cpp-header",
    )


def _cpp_source_plan(request: str) -> Plan:
    """Create a matching C++ source file for a class."""
    rules = load_rules()["cpp"]
    class_name = _extract_class_name(request)
    source_dir = rules.get("source_dir", "src")
    extension = rules.get("source_extension", ".cpp")
    header_ext = rules.get("header_extension", ".hpp")
    path = _extract_path_after_keywords(request, ["at", "in", "into", "nach", "unter"], f"{source_dir}/{class_name}{extension}")
    content = f'#include "{class_name}{header_ext}"\n\n{class_name}::{class_name}() = default;\n{class_name}::~{class_name}() = default;\n'
    return Plan(
        summary=f"Create C++ source for class {class_name}.",
        steps=[
            CommandStep(kind="mkdir", path=str(Path(path).parent), description="Create source parent directory.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=content, description=f"Write source file for {class_name}.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=path)],
        source="template:cpp-source",
    )


def _cmake_plan(_: str) -> Plan:
    """Create a generic CMakeLists.txt for a small C++ project."""
    rules = load_rules()["cpp"]
    name = Path.cwd().name.replace("-", "_")
    content = f"""cmake_minimum_required(VERSION 3.16)
project({name})

set(CMAKE_CXX_STANDARD {rules.get('standard', '17')})
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB_RECURSE SOURCES CONFIGURE_DEPENDS src/*.cpp)
add_executable(${{PROJECT_NAME}} ${{SOURCES}})
target_include_directories(${{PROJECT_NAME}} PRIVATE include)
"""
    return Plan(
        summary="Create CMakeLists.txt.",
        steps=[CommandStep(kind="write_file", path="CMakeLists.txt", content=content, description="Write a small C++ CMake file.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="CMakeLists.txt")],
        source="template:cmake",
    )


def _node_project_plan(request: str, vite: bool = False) -> Plan:
    name = _extract_name(request, default="app")
    if vite:
        return Plan(
            summary=f"Create a Vite project named {name}.",
            steps=[CommandStep(kind="command", command=f"npm create vite@latest {name}", description="Run the official Vite project generator.", changes_files=True, risk="medium")],
            risk="medium",
            notes=["Package generation requires confirmation before npm runs."],
            source="template:vite-project",
        )
    package_json = f"""{{ 
  "name": "{name}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "test": "node --test"
  }}
}}
"""
    return Plan(
        summary=f"Create a Node project named {name}.",
        steps=[
            CommandStep(kind="mkdir", path=name, description="Create project directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/package.json", content=package_json, description="Create package.json.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=f"{name}/package.json")],
        source="template:node-project",
    )


def _package_json_plan(_: str) -> Plan:
    name = Path.cwd().name.replace("_", "-")
    content = f"""{{ 
  "name": "{name}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "test": "node --test"
  }}
}}
"""
    return Plan(
        summary="Create package.json.",
        steps=[CommandStep(kind="write_file", path="package.json", content=content, description="Create a minimal package.json.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="package.json")],
        source="template:package-json",
    )


def _rust_project_plan(request: str) -> Plan:
    name = _extract_name(request, default="tool")
    return Plan(
        summary=f"Create a Rust project named {name}.",
        steps=[CommandStep(kind="command", command=f"cargo new {name}", description="Run cargo new.", changes_files=True, risk="medium")],
        risk="medium",
        source="template:rust-project",
    )


def _c_project_plan(request: str) -> Plan:
    name = _extract_name(request, default="embedded")
    main_c = '#include <stdio.h>\n\nint main(void) {\n    puts("Hello from CAIROS!");\n    return 0;\n}\n'
    makefile = f"""CC ?= cc
CFLAGS ?= -Wall -Wextra -std=c11

.PHONY: all clean test

all: {name}

{name}: src/main.c
\t$(CC) $(CFLAGS) -o $@ $<

test: all
\t./{name}

clean:
\trm -f {name}
"""
    return Plan(
        summary=f"Create a C project named {name}.",
        steps=[
            CommandStep(kind="mkdir", path=f"{name}/src", description="Create source directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/src/main.c", content=main_c, description="Create main.c.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/Makefile", content=makefile, description="Create Makefile.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=f"{name}/src/main.c")],
        source="template:c-project",
    )


def _requirements_plan(_: str) -> Plan:
    return Plan(
        summary="Create requirements.txt.",
        steps=[CommandStep(kind="write_file", path="requirements.txt", content="", description="Create an empty requirements.txt.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="requirements.txt")],
        source="template:requirements",
    )


def _pyproject_plan(_: str) -> Plan:
    name = Path.cwd().name.replace("_", "-")
    content = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []
"""
    return Plan(
        summary="Create pyproject.toml.",
        steps=[CommandStep(kind="write_file", path="pyproject.toml", content=content, description="Create a minimal pyproject.toml.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="pyproject.toml")],
        source="template:pyproject",
    )


def _append_requirement_plan(package: str) -> Plan:
    return Plan(
        summary=f"Add {package} to requirements.txt.",
        steps=[CommandStep(kind="append_file", path="requirements.txt", content=f"{package}\n", description=f"Append {package} dependency.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="requirements.txt")],
        source="template:add-python-dependency",
    )


def _makefile_plan(_: str) -> Plan:
    content = """.PHONY: test build clean

test:
\tpython -m pytest

build:
\tpython -m compileall -q .

clean:
\trm -rf build dist .pytest_cache
"""
    return Plan(
        summary="Create Makefile.",
        steps=[CommandStep(kind="write_file", path="Makefile", content=content, description="Create standard test/build/clean targets.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="Makefile")],
        source="template:makefile",
    )


def _extract_script_name(request: str) -> str:
    patterns = [
        rf"(?:script|skript)\s+({PROJECT_NAME_RE}(?:\.sh)?)",
        rf"(?:named|called|namens)\s+({PROJECT_NAME_RE}(?:\.sh)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, request, flags=re.IGNORECASE)
        if match:
            name = match.group(1)
            if name.lower() in {"that", "to", "which", "who", "what"}:
                continue
            return name if name.endswith(".sh") else f"{name}.sh"
    return "branch_info.sh" if "branch" in request.lower() else "script.sh"


def _bash_script_plan(request: str) -> Plan:
    """Create common Bash helper scripts deterministically."""
    path = _extract_script_name(request)
    safe_path = _safe_rel_path(path)
    if safe_path is None:
        return _unsafe_path_plan(path)
    lowered = request.lower()
    if "branch" in lowered and ("folder" in lowered or "pwd" in lowered or "directory" in lowered):
        content = """#!/usr/bin/env bash
set -euo pipefail

echo "Current folder: $(pwd)"
branch="$(git branch --show-current 2>/dev/null || true)"
if [ -n "$branch" ]; then
  echo "Current git branch: $branch"
else
  echo "Current git branch: not a git repository"
fi
"""
        summary = "Create a Bash script that prints the current folder and git branch."
    elif "hello" in lowered:
        content = """#!/usr/bin/env bash
set -euo pipefail

echo "hello world"
"""
        summary = "Create a Bash script that prints hello world."
    else:
        content = """#!/usr/bin/env bash
set -euo pipefail

echo "TODO: add setup commands"
"""
        summary = "Create an executable Bash script."
    quoted = shlex.quote(safe_path)
    return Plan(
        summary=summary,
        steps=[
            CommandStep(kind="write_file", path=safe_path, content=content, description=f"Write {safe_path}.", changes_files=True),
            CommandStep(kind="command", command=f"chmod +x {quoted}", description=f"Make {safe_path} executable.", changes_files=True, risk="medium"),
        ],
        risk="medium",
        verification=[VerificationStep(kind="file_exists", target=safe_path)],
        source="template:bash_script",
    )


def _create_folder_plan(request: str) -> Plan:
    match = re.search(r"\b(?:make|create|mkdir|mache|macke|mach|erstelle|erstell)\s+(?:nested\s+)?(?:folder|directory|dir|ordner|verzeichnis)\s+(.+)$", request, flags=re.IGNORECASE)
    if not match:
        return _unsafe_path_plan("<missing-folder-name>")
    name = match.group(1).strip().strip('"').strip("'")
    safe_name = _safe_rel_path(name)
    if safe_name is None:
        return _unsafe_path_plan(name)
    return Plan(
        summary=f"Create folder {safe_name}.",
        steps=[CommandStep(kind="mkdir", path=safe_name, description=f"Create directory {safe_name}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=safe_name)],
        source="template:folder",
    )


def _create_file_plan(request: str) -> Plan:
    match = re.search(rf"\b(?:create|make|touch|erstelle|erstell|mache|macke)\s+(?:a\s+|an\s+)?(?:empty\s+)?(?:file|datei)\s+(?:(?:named|called|namens)\s+)?(?:{NAMED_VALUE_RE})(?:\s+with\s+(.+))?\s*$", request, flags=re.IGNORECASE)
    if not match:
        return _unsafe_path_plan("<missing-file-name>")
    path = _first_group(match)
    content_hint = match.group(4) if len(match.groups()) >= 4 else None
    safe_path = _safe_rel_path(path)
    if safe_path is None:
        return _unsafe_path_plan(path)
    content = ""
    summary = f"Create empty file {safe_path}."
    if content_hint:
        if "hello world" in content_hint.lower():
            content = "hello world\n"
            summary = f"Create file {safe_path} with hello world."
        else:
            content = content_hint.strip() + "\n"
            summary = f"Create file {safe_path} with requested text."
    return Plan(
        summary=summary,
        steps=[CommandStep(kind="write_file", path=safe_path, content=content, description=f"Write {safe_path}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=safe_path)],
        source="template:file",
    )


def _append_todo_plan(request: str) -> Plan:
    match = re.search(r"\bappend\s+(.+?)\s+to\s+([a-zA-Z0-9_./-]+)\s*$", request, flags=re.IGNORECASE)
    text = match.group(1).strip() if match else "TODO"
    path = match.group(2).strip() if match else "README.md"
    safe_path = _safe_rel_path(path)
    if safe_path is None:
        return _unsafe_path_plan(path)
    if text.lower() == "todo":
        text = "- TODO\n"
    else:
        text = text + "\n"
    return Plan(
        summary=f"Append text to {safe_path}.",
        steps=[CommandStep(kind="append_file", path=safe_path, content=text, description=f"Append to {safe_path}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=safe_path)],
        source="template:append-file",
    )


def _readme_plan(request: str) -> Plan:
    name = _extract_name(request, default=Path.cwd().name)
    return Plan(
        summary="Create or replace README.md.",
        steps=[CommandStep(kind="write_file", path="README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Write a simple README.md.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="README.md")],
        source="template:readme",
    )


def _gitignore_plan(request: str) -> Plan:
    text = request.lower()
    if "node" in text:
        content = "node_modules/\ndist/\nbuild/\n.env\n.DS_Store\nnpm-debug.log*\n"
        source = "template:gitignore-node"
        summary = "Create Node .gitignore."
    elif "cpp" in text or "c++" in text or re.search(r"\bc\b", text):
        content = "build/\ncmake-build-*/\nCMakeFiles/\nCMakeCache.txt\ncompile_commands.json\n*.o\n*.obj\n*.exe\n.DS_Store\n"
        source = "template:gitignore-cpp"
        summary = "Create C/C++ .gitignore."
    elif "rust" in text:
        content = "target/\nCargo.lock\n.DS_Store\n"
        source = "template:gitignore-rust"
        summary = "Create Rust .gitignore."
    else:
        content = ".venv/\nvenv/\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\nbuild/\ndist/\ncmake-build-*/\n.vscode/\n.idea/\n"
        source = "template:gitignore"
        summary = "Create a useful Python/C++ .gitignore."
    return Plan(
        summary=summary,
        steps=[CommandStep(kind="write_file", path=".gitignore", content=content, description="Write .gitignore.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=".gitignore")],
        source=source,
    )


def _git_finish_plan(_: str) -> Plan:
    rules = load_rules()["git"]
    remote = rules.get("remote", "origin")
    main_branch = rules.get("main_branch", "main")
    return Plan(
        summary="Safely inspect current branch before merging or pushing.",
        steps=[
            CommandStep(kind="command", command="git status --short", description="Inspect uncommitted local changes."),
            CommandStep(kind="command", command="git branch --show-current", description="Print the current branch."),
            CommandStep(kind="command", command=f"git fetch {remote}", description="Fetch latest remote refs without merging."),
            CommandStep(kind="command", command=f"git log --oneline --decorate --graph --max-count=12 --all", description="Show recent local and remote commit graph."),
            CommandStep(kind="command", command=f"git log --oneline --left-right --cherry-pick HEAD...{remote}/{main_branch}", description="Compare current HEAD with remote main."),
        ],
        risk="medium",
        notes=[
            "This workflow intentionally does not merge or push automatically.",
            f"Review the comparison with {remote}/{main_branch}. Then explicitly ask CAIROS for merge/rebase/push next step.",
        ],
        source="template:git-safe-workflow",
        requires_confirmation=False,
    )


def _git_inspection_plan(request: str) -> Plan:
    """Create a read-only git inspection plan."""
    text = request.lower()
    push = "push" in text
    steps = [
        CommandStep(kind="command", command="git status --short", description="Show changed, staged and untracked files."),
        CommandStep(kind="command", command="git branch --show-current", description="Show the current branch."),
        CommandStep(kind="command", command="git log --oneline --decorate --graph --max-count=10", description="Show recent commits."),
        CommandStep(kind="command", command="git diff --stat", description="Show unstaged change summary."),
        CommandStep(kind="command", command="git diff --cached --stat", description="Show staged change summary."),
    ]
    if push:
        steps.insert(0, CommandStep(kind="command", command="git fetch origin", description="Update origin remote-tracking references."))
        steps.append(CommandStep(kind="command", command="git log --oneline --left-right --cherry-pick HEAD...origin/main", description="Compare current branch with origin/main."))
    return Plan(
        summary="Inspect repository status and recent commits.",
        steps=steps,
        risk="low",
        requires_confirmation=False,
        source="template:git-inspection",
    )


def _git_commit_plan(request: str) -> Plan:
    match = re.search(r"message\s+(.+)$", request, flags=re.IGNORECASE)
    message = (match.group(1).strip().strip('"').strip("'") if match else "update")
    quoted = shlex.quote(message)
    return Plan(
        summary=f"Add all changes and commit with message {message!r}.",
        steps=[
            CommandStep(kind="command", command="git add -A", description="Stage all current changes.", changes_files=True, risk="medium"),
            CommandStep(kind="command", command=f"git commit -m {quoted}", description="Create a git commit.", changes_files=True, risk="medium"),
        ],
        risk="medium",
        verification=[VerificationStep(kind="command_output_equals", target="git log -1 --pretty=format:%s", expected=message)],
        source="template:git-commit",
    )


def _create_folders_plan(request: str) -> Plan:
    match = re.search(r"\b(?:create|make|mkdir)\s+folders\s+(.+)$", request, flags=re.IGNORECASE)
    raw = match.group(1) if match else "src tests docs"
    names = [part for part in re.split(r"[\s,]+", raw) if part and part.lower() not in {"and", "folders", "folder"}]
    safe_names: list[str] = []
    for name in names:
        safe = _safe_rel_path(name.strip('"').strip("'"))
        if safe is None:
            return _unsafe_path_plan(name)
        safe_names.append(safe)
    return Plan(
        summary=f"Create folders {', '.join(safe_names)}.",
        steps=[CommandStep(kind="mkdir", path=name, description=f"Create directory {name}.", changes_files=True) for name in safe_names],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=name) for name in safe_names],
        source="template:folders",
    )


def _editorconfig_plan(_: str) -> Plan:
    content = """root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4

[*.{json,md,yml,yaml}]
indent_size = 2
"""
    return Plan(
        summary="Create .editorconfig.",
        steps=[CommandStep(kind="write_file", path=".editorconfig", content=content, description="Write .editorconfig.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=".editorconfig")],
        source="template:editorconfig",
    )


def _env_example_plan(_: str) -> Plan:
    content = "# Copy to .env and fill in local values. Do not commit real secrets.\nGEMINI_API_KEY=\nOPENAI_API_KEY=\n"
    return Plan(
        summary="Create .env.example without secrets.",
        steps=[CommandStep(kind="write_file", path=".env.example", content=content, description="Write .env.example.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=".env.example")],
        source="template:env-example",
    )


def _mit_license_plan(_: str) -> Plan:
    content = """MIT License

Copyright (c) YEAR AUTHOR

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""
    return Plan(
        summary="Create MIT LICENSE file.",
        steps=[CommandStep(kind="write_file", path="LICENSE", content=content, description="Write MIT license template.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="LICENSE")],
        source="template:license-mit",
    )


def _repo_setup_plan(_: str) -> Plan:
    return Plan(
        summary="Inspect and initialize common project structure.",
        steps=[
            CommandStep(kind="command", command="git status --short --branch", description="Inspect git state."),
            CommandStep(kind="mkdir", path="src", description="Create src directory if missing.", changes_files=True),
            CommandStep(kind="mkdir", path="tests", description="Create tests directory if missing.", changes_files=True),
            CommandStep(kind="mkdir", path="docs", description="Create docs directory if missing.", changes_files=True),
            CommandStep(kind="write_file", path="README.md", content=f"# {Path.cwd().name}\n\n", description="Create README if desired.", changes_files=True),
        ],
        risk="medium",
        notes=["Review existing files before running; this may create or replace README.md."],
        verification=[VerificationStep(kind="dir_exists", target="src"), VerificationStep(kind="dir_exists", target="tests")],
        source="template:repo-setup",
    )


def _python_config_plan(kind: str) -> Plan:
    configs = {
        "pytest": ("pytest.ini", "[pytest]\ntestpaths = tests\npython_files = test_*.py\n"),
        "ruff": ("ruff.toml", "line-length = 100\ntarget-version = \"py310\"\n"),
        "black": ("pyproject.toml", "[tool.black]\nline-length = 100\ntarget-version = ['py310']\n"),
        "mypy": ("mypy.ini", "[mypy]\npython_version = 3.10\nwarn_unused_ignores = True\n"),
    }
    path, content = configs[kind]
    return Plan(
        summary=f"Create {kind} configuration.",
        steps=[CommandStep(kind="write_file", path=path, content=content, description=f"Write {path}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=path)],
        source=f"template:{kind}-config",
    )


def _python_module_plan(request: str) -> Plan:
    name = _extract_name(request, default="calculator").replace("-", "_")
    safe = _safe_rel_path(name)
    if safe is None:
        return _unsafe_path_plan(name)
    return Plan(
        summary=f"Create Python package module {safe}.",
        steps=[
            CommandStep(kind="mkdir", path=safe, description="Create package directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{safe}/__init__.py", content="", description="Write package initializer.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=f"{safe}/__init__.py")],
        source="template:python-module",
    )


def _python_test_file_plan(request: str) -> Plan:
    name = _extract_name(request, default="calculator").replace("-", "_")
    safe = _safe_rel_path(name)
    if safe is None:
        return _unsafe_path_plan(name)
    content = f"def test_{safe}_placeholder():\n    assert True\n"
    return Plan(
        summary=f"Create pytest file for module {safe}.",
        steps=[
            CommandStep(kind="mkdir", path="tests", description="Create tests directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"tests/test_{safe}.py", content=content, description="Write pytest file.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=f"tests/test_{safe}.py")],
        source="template:python-test-file",
    )


def _powershell_script_plan(request: str) -> Plan:
    match = re.search(r"(?:script|skript)\s+([a-zA-Z][a-zA-Z0-9_-]*)(?:\.ps1)?", request, flags=re.IGNORECASE)
    name = match.group(1) if match else "repo_info"
    path = name if name.endswith(".ps1") else f"{name}.ps1"
    safe = _safe_rel_path(path)
    if safe is None:
        return _unsafe_path_plan(path)
    content = """Write-Output "Current folder: $(Get-Location)"
$branch = git branch --show-current 2>$null
if ($branch) {
    Write-Output "Current git branch: $branch"
} else {
    Write-Output "Current git branch: not a git repository"
}
"""
    return Plan(
        summary="Create a PowerShell script that prints the current folder and git branch.",
        steps=[CommandStep(kind="write_file", path=safe, content=content, description=f"Write {safe}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=safe)],
        source="template:powershell-script",
    )


def _wsl_plan(request: str) -> Plan | None:
    text = request.lower()
    distro = _extract_named_value(request, "any")
    distro_match = re.search(r"\bwsl\s+(?:distro|distribution)\s+([A-Za-z][A-Za-z0-9_.-]*)", request, flags=re.IGNORECASE)
    if not distro_match:
        distro_match = re.search(r"\b(?:wsl2?|distro|distribution)\s+([A-Za-z][A-Za-z0-9_.-]*)", request, flags=re.IGNORECASE)
    if distro_match and distro_match.group(1).lower() not in {"distro", "distribution", "distros"}:
        distro = distro_match.group(1)
    if "list" in text or "show wsl distros" in text:
        return _simple_command_plan("List WSL distributions.", "wsl -l -v", "template:wsl-list", confirm=False)
    if "status" in text:
        return _simple_command_plan("Show WSL status.", "wsl --status", "template:wsl-status", confirm=False)
    if "shutdown" in text and ("all" in text or "distros" in text or "wsl" in text and not distro):
        return _simple_command_plan("Shutdown all WSL distributions.", "wsl --shutdown", "template:wsl-shutdown", risk="medium", changes=True)
    if ("terminate" in text or "shutdown" in text or "stop" in text) and distro:
        safe = _safe_rel_path(distro)
        if safe is None:
            return _unsafe_path_plan(distro)
        return _simple_command_plan(f"Terminate WSL distribution {safe}.", f"wsl --terminate {shlex.quote(safe)}", "template:wsl-terminate", risk="medium", changes=True)
    if "start" in text and distro:
        safe = _safe_rel_path(distro)
        if safe is None:
            return _unsafe_path_plan(distro)
        plan = _simple_command_plan(f"Start WSL distribution {safe}.", f"wsl -d {shlex.quote(safe)}", "template:wsl-start", risk="medium", changes=True)
        plan.notes.append("Starting a WSL distro may open an interactive session and take over the terminal.")
        return plan
    if "explorer" in text or "folder" in text:
        return _simple_command_plan("Open the current WSL folder in Windows Explorer.", "explorer.exe .", "template:wsl-explorer", confirm=False)
    return None


def _system_plan(request: str) -> Plan | None:
    text = request.lower()
    if "disk" in text and ("usage" in text or "space" in text):
        return _simple_command_plan("Show disk usage.", "df -h && du -sh .", "template:system-disk", confirm=False)
    if "memory" in text:
        return _simple_command_plan("Show memory usage.", "free -h", "template:system-memory", confirm=False)
    if "current shell" in text:
        return _simple_command_plan("Show the current shell.", "echo $SHELL", "template:system-shell", confirm=False)
    if "listening ports" in text:
        return _simple_command_plan("List listening ports.", "ss -tulpn", "template:system-ports", confirm=False)
    if "python processes" in text:
        return _simple_command_plan("Show running Python processes.", "ps aux | grep '[p]ython'", "template:system-python-processes", confirm=False)
    port_match = re.search(r"port\s+(\d+)", text)
    if "kill" in text and port_match:
        port = port_match.group(1)
        return _simple_command_plan(f"Inspect processes using port {port} before killing.", f"lsof -i :{port}", "template:system-kill-port-inspect", risk="medium", confirm=True)
    return None


def _windows_plan(request: str) -> Plan | None:
    text = request.lower()
    if "explorer" in text or ("open" in text and "current folder" in text):
        return _simple_command_plan("Open the current folder in Explorer.", "explorer .", "template:windows-explorer", confirm=False)
    if "vscode" in text or "vs code" in text:
        return _simple_command_plan("Open the current project in VS Code.", "code .", "template:vscode-open", confirm=False)
    if "powershell version" in text:
        return _simple_command_plan("Show PowerShell version.", "$PSVersionTable.PSVersion", "template:powershell-version", confirm=False)
    if re.search(r"\bshow\s+path\b", text):
        return _simple_command_plan("Show PATH.", "echo $PATH", "template:show-path", confirm=False)
    if "add" in text and ".local/bin" in text and "path" in text:
        return Plan(
            summary="Print instructions to add ~/.local/bin to PATH.",
            steps=[CommandStep(kind="command", command="printf '%s\n' 'Add this to your shell profile: export PATH=\"$HOME/.local/bin:$PATH\"'", description="Print PATH instructions.")],
            risk="low",
            requires_confirmation=False,
            source="template:path-instructions",
        )
    if "environment variable" in text:
        match = re.search(r"environment variable\s+([A-Z_][A-Z0-9_]*)", request, flags=re.IGNORECASE)
        name = match.group(1) if match else "GEMINI_API_KEY"
        return _simple_command_plan(f"Show whether {name} is set without printing its value.", f"test -n \"${name}\" && echo '{name}=set' || echo '{name}=not set'", "template:env-status", confirm=False)
    if "gemini" in text and "key" in text and ("set" in text or "env" in text):
        return Plan(
            summary="Print safe Gemini API key setup commands.",
            steps=[CommandStep(kind="command", command="printf '%s\n' 'PowerShell: setx GEMINI_API_KEY \"your-key\"' 'Current shell: export GEMINI_API_KEY=\"your-key\"'", description="Print secret setup instructions.")],
            risk="low",
            requires_confirmation=False,
            notes=["Do not paste real API keys into CAIROS commands, commits or logs."],
            source="template:gemini-key-instructions",
        )
    return None


def _package_install_plan(request: str) -> Plan | None:
    text = request.lower()
    if "python" in text or Path("requirements.txt").exists() or Path("pyproject.toml").exists():
        return _simple_command_plan("Install Python dependencies.", "python -m pip install -r requirements.txt", "template:pip-install", risk="medium", changes=True)
    if "npm" in text or "node" in text or Path("package.json").exists():
        return _simple_command_plan("Install npm dependencies.", "npm install", "template:npm-install", risk="medium", changes=True)
    if "rust" in text or "cargo" in text or Path("Cargo.toml").exists():
        return _simple_command_plan("Fetch/build Rust dependencies.", "cargo build", "template:cargo-build", risk="medium", changes=True)
    return None


def _cleanup_plan(request: str) -> Plan | None:
    text = request.lower()
    if "node_modules" in text:
        return _simple_command_plan("Remove node_modules.", "rm -rf node_modules", "template:cleanup-node-modules", risk="medium", changes=True)
    if "pytest_cache" in text:
        return _simple_command_plan("Remove .pytest_cache.", "rm -rf .pytest_cache", "template:cleanup-pytest-cache", risk="medium", changes=True)
    if "dist" in text:
        return _simple_command_plan("Remove dist folder.", "rm -rf dist", "template:cleanup-dist", risk="medium", changes=True)
    if "build" in text:
        return _simple_command_plan("Remove build folder.", "rm -rf build", "template:cleanup-build-folder", risk="medium", changes=True)
    if "temporary" in text or "temp" in text:
        return _simple_command_plan("Remove common local temporary files.", "find . -maxdepth 2 \\( -name '*~' -o -name '*.tmp' -o -name '*.bak' \\) -delete", "template:cleanup-temp", risk="medium", changes=True)
    return None


def _simple_command_plan(summary: str, command: str, source: str, risk: str = "low", changes: bool = False, confirm: bool | None = None) -> Plan:
    return Plan(
        summary=summary,
        steps=[CommandStep(kind="command", command=command, description=summary, changes_files=changes, risk=risk)],
        risk=risk,  # type: ignore[arg-type]
        requires_confirmation=(changes if confirm is None else confirm),
        source=source,
    )


def _echo_plan(request: str) -> Plan | None:
    match = re.match(r"\s*(?:say|echo|print|sag)\s+(.+?)\s*$", request, flags=re.IGNORECASE)
    if not match:
        return None
    text = match.group(1).strip()
    if not text:
        return None
    return _simple_command_plan("Print text.", f"echo {shlex.quote(text)}", "template:echo", confirm=False)


def _cd_warning_plan(request: str) -> Plan | None:
    text = request.lower()
    if not (re.search(r"\b(?:go|cd|change)\s+(?:into|to)\s+(?:(?:directory|folder)\s+)?", text) or "using the find command" in text and "directory" in text):
        return None
    name = _extract_named_value(request, "any")
    if not name:
        match = re.search(r"(?:directory|folder)\s+([A-Za-z0-9_.-]+)", request, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"\b(?:go|cd|change)\s+(?:into|to)\s+([A-Za-z0-9_.-]+)", request, flags=re.IGNORECASE)
        name = match.group(1) if match else "<name>"
    return Plan(
        summary="Explain how to change directories from the parent shell.",
        steps=[
            CommandStep(
                kind="command",
                command=f"find . -maxdepth 4 -type d -iname {shlex.quote(name)} -print",
                description="Print matching directory paths; use a shell wrapper to cd into one.",
            )
        ],
        risk="low",
        requires_confirmation=False,
        notes=[
            "CAIROS cannot permanently change the parent shell directory from a normal child process.",
            "Use a shell wrapper around `cairos find-dir <name>` or copy one of the printed paths into `cd`.",
        ],
        source="template:cd-guidance",
    )


def _has_multiple_creation_targets(tokens: list[str], text: str) -> bool:
    """Return True when a request mentions multiple things to create."""
    target_count = 0
    for concept in ("folder", "file", "class", "project", "header", "source"):
        if has_concept(tokens, concept):
            target_count += 1
    content_words = {"contains", "containing", "function", "main", "headerguard", "headerguards", "ifndef"}
    return target_count >= 2 and (" with " in text or " named " in text or any(word in tokens for word in content_words))


def _looks_like_cpp_compound_request(tokens: list[str], text: str) -> bool:
    has_folder = has_concept(tokens, "folder") or "project folder" in text
    has_file = has_concept(tokens, "file") or ".cpp" in text
    has_cpp_content = has_concept(tokens, "cpp") or "main" in tokens or "ifndef" in tokens or "headerguards" in tokens or has_concept(tokens, "class")
    has_names = _extract_named_value(text, "folder") is not None and _extract_named_value(text, "file") is not None
    return has_folder and has_file and has_cpp_content and has_names and has_concept(tokens, "make")


def _run_tests_plan(_: str) -> Plan:
    if Path("Makefile").exists():
        command = "make test"
    elif Path("pyproject.toml").exists():
        command = "python -m pytest"
    elif Path("CMakeLists.txt").exists():
        command = "cmake --build build && ctest --test-dir build"
    else:
        command = "python -m pytest"
    return Plan(
        summary="Run the detected project test command.",
        steps=[CommandStep(kind="command", command=command, description="Run tests for the current project.")],
        risk="low",
        requires_confirmation=False,
        source="template:test-runner",
    )


def plan_from_template(request: str) -> Plan | None:
    """Return a deterministic plan for a known request, or ``None``."""
    tokens = tokenize(request)
    text = request.lower()

    echo_plan = _echo_plan(request)
    if echo_plan:
        return echo_plan

    cd_plan = _cd_warning_plan(request)
    if cd_plan:
        return cd_plan

    if "powershell" in tokens and ("script" in tokens or "ps1" in text) and has_concept(tokens, "make"):
        return _powershell_script_plan(request)

    if _looks_like_cpp_compound_request(tokens, text):
        return _cpp_compound_plan(request)

    if has_concept(tokens, "folder") and has_concept(tokens, "file") and _extract_named_value(request, "folder") and _extract_named_value(request, "file"):
        return _folder_file_compound_plan(request)

    if has_concept(tokens, "cpp") and "mini" in tokens and has_concept(tokens, "project") and has_concept(tokens, "class") and "main" in tokens:
        return _cpp_mini_project_plan(request)

    if ("script" in tokens or "skript" in tokens) and (has_concept(tokens, "make") or "executable" in tokens):
        return _bash_script_plan(request)

    if "wsl" in text:
        wsl_plan = _wsl_plan(request)
        if wsl_plan:
            return wsl_plan

    if any(word in text for word in ["explorer", "vscode", "vs code", "powershell version", "show path", "environment variable", "gemini api key"]):
        windows_plan = _windows_plan(request)
        if windows_plan:
            return windows_plan

    if any(phrase in text for phrase in ["disk usage", "memory usage", "current shell", "list listening ports", "python processes", "kill process by port"]):
        system_plan = _system_plan(request)
        if system_plan:
            return system_plan

    if "commit" in tokens and "add" in tokens and "message" in tokens:
        return _git_commit_plan(request)

    if (
        ("commit" in tokens and ("log" in tokens or "summarize" in tokens or "summary" in tokens or "inspect" in tokens or "check" in tokens))
        or ("repo" in tokens and ("ready" in tokens or "clean" in tokens or "summary" in tokens))
        or ("branch" in tokens and ("current" in tokens or "summarize" in tokens or "check" in tokens))
        or ("git" in tokens and "summary" in tokens)
        or ("ready" in tokens and ("commit" in tokens or "push" in tokens))
    ):
        return _git_inspection_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "python") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _python_project_plan(request)

    if "python" in tokens and "cli" in tokens and has_concept(tokens, "app") and has_concept(tokens, "make"):
        return _python_project_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "cpp") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _cpp_project_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "c") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _c_project_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "header") and (has_concept(tokens, "cpp") or has_concept(tokens, "class") or has_concept(tokens, "make") or "hpp" in text):
        return _cpp_header_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "cpp") and has_concept(tokens, "class") and has_concept(tokens, "make"):
        return _cpp_header_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and has_concept(tokens, "source") and (has_concept(tokens, "cpp") or has_concept(tokens, "class")):
        return _cpp_source_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and "cmake" in text and has_concept(tokens, "file"):
        return _cmake_plan(request)

    if has_concept(tokens, "node") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _node_project_plan(request)

    if has_concept(tokens, "package") and "json" in tokens and has_concept(tokens, "make"):
        return _package_json_plan(request)

    if "vite" in tokens and has_concept(tokens, "project"):
        return _node_project_plan(request, vite=True)

    if has_concept(tokens, "rust") and (has_concept(tokens, "project") or "cargo" in tokens) and has_concept(tokens, "make"):
        return _rust_project_plan(request)

    if has_concept(tokens, "requirements") and has_concept(tokens, "make"):
        return _requirements_plan(request)

    if "freeze" in tokens and "requirements" in tokens:
        return _simple_command_plan("Freeze installed Python packages to requirements.txt.", "python -m pip freeze > requirements.txt", "template:freeze-requirements", risk="medium", changes=True)

    if "update" in tokens and "requirements" in tokens:
        return _simple_command_plan("Update Python dependencies from requirements.txt.", "python -m pip install --upgrade -r requirements.txt", "template:update-requirements", risk="medium", changes=True)

    if "pyproject" in text and has_concept(tokens, "make"):
        return _pyproject_plan(request)

    if "pytest" in tokens and "config" in tokens:
        return _python_config_plan("pytest")
    if "ruff" in tokens and "config" in tokens:
        return _python_config_plan("ruff")
    if "black" in tokens and "config" in tokens:
        return _python_config_plan("black")
    if "mypy" in tokens and "config" in tokens:
        return _python_config_plan("mypy")

    if "package" in tokens and "module" in tokens and has_concept(tokens, "python"):
        return _python_module_plan(request)

    if "test" in tokens and "file" in tokens and "module" in tokens:
        return _python_test_file_plan(request)

    if has_concept(tokens, "makefile") and has_concept(tokens, "make"):
        return _makefile_plan(request)

    if ("env example" in text or ".env.example" in text) and has_concept(tokens, "make"):
        return _env_example_plan(request)

    if "pytest" in tokens and "add" in tokens:
        return _append_requirement_plan("pytest")
    if "typer" in tokens and "add" in tokens:
        return _append_requirement_plan("typer")
    if "rich" in tokens and "add" in tokens:
        return _append_requirement_plan("rich")

    if has_concept(tokens, "venv") and has_concept(tokens, "make"):
        return Plan(
            summary="Create a Python virtual environment in the current directory.",
            steps=[CommandStep(kind="command", command="python3 -m venv .venv", description="Create .venv.", changes_files=True)],
            risk="low",
            notes=["Activate it with: source .venv/bin/activate"],
            verification=[VerificationStep(kind="dir_exists", target=".venv")],
            source="template:venv",
        )

    if has_all(request, "git", "make") and ("init" in tokens or "initialize" in tokens or "initialisiere" in text):
        return Plan(
            summary="Initialize a git repository in the current directory.",
            steps=[CommandStep(kind="command", command="git init", description="Initialize git.", changes_files=True)],
            risk="low",
            source="template:git-init",
        )

    if "setup this repo" in text or "initialize this project" in text or "create project structure" in text:
        return _repo_setup_plan(request)

    if "inspect this repo" in text:
        return _git_inspection_plan(request)

    if "docs folder" in text and "readme" in text and has_concept(tokens, "make"):
        return Plan(
            summary="Create docs folder and README.md.",
            steps=[
                CommandStep(kind="mkdir", path="docs", description="Create docs directory.", changes_files=True),
                CommandStep(kind="write_file", path="README.md", content=f"# {Path.cwd().name}\n\n", description="Write README.md.", changes_files=True),
            ],
            risk="low",
            verification=[VerificationStep(kind="dir_exists", target="docs"), VerificationStep(kind="file_exists", target="README.md")],
            source="template:docs-readme",
        )

    if re.search(r"\b(?:create|make|mkdir)\s+folders\s+", text):
        return _create_folders_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and re.search(r"\b(?:make|create|mkdir|mache|macke|mach|erstelle|erstell)\s+(?:nested\s+)?(?:folder|directory|dir|ordner|verzeichnis)\s+\S+", text):
        return _create_folder_plan(request)

    if not _has_multiple_creation_targets(tokens, text) and re.search(rf"\b(?:create|make|touch|erstelle|erstell|mache|macke)\s+(?:a\s+|an\s+)?(?:empty\s+)?(?:file|datei)\s+(?:(?:named|called|namens)\s+)?(?:{NAMED_VALUE_RE})(?:\s+with\s+.+)?\s*$", request, flags=re.IGNORECASE):
        return _create_file_plan(request)

    if text.startswith("append ") and " to " in text:
        return _append_todo_plan(request)

    if has_concept(tokens, "readme") and has_concept(tokens, "make"):
        return _readme_plan(request)

    if has_concept(tokens, "gitignore") and has_concept(tokens, "make"):
        return _gitignore_plan(request)

    if "editorconfig" in text and has_concept(tokens, "make"):
        return _editorconfig_plan(request)

    if "license" in tokens and "mit" in tokens and has_concept(tokens, "make"):
        return _mit_license_plan(request)

    if has_concept(tokens, "large") and "file" in text:
        return Plan(
            summary="Find large files below the current directory.",
            steps=[CommandStep(kind="command", command="find . -type f -size +100M -print", description="List files larger than 100 MB.")],
            risk="low",
            requires_confirmation=False,
            source="template:find-large-files",
        )

    if has_concept(tokens, "clean") and has_concept(tokens, "pycache"):
        return Plan(
            summary="Remove Python bytecode cache folders.",
            steps=[CommandStep(kind="command", command="find . -type d -name __pycache__ -prune -exec rm -rf {} +", description="Delete generated __pycache__ folders only.", changes_files=True, risk="medium")],
            risk="medium",
            notes=["This removes generated Python cache folders only."],
            source="template:clean-pycache",
        )

    if has_concept(tokens, "status") and has_concept(tokens, "git"):
        return Plan(
            summary="Show compact git status.",
            steps=[CommandStep(kind="command", command="git status --short --branch", description="Show branch and working tree status.")],
            risk="low",
            requires_confirmation=False,
            source="template:git-status",
        )

    if "show" in tokens and "changed" in tokens and "files" in tokens:
        return _simple_command_plan("Show changed files.", "git diff --name-status", "template:git-changed-files", confirm=False)

    if "show" in tokens and "staged" in tokens and "files" in tokens:
        return _simple_command_plan("Show staged files.", "git diff --cached --name-status", "template:git-staged-files", confirm=False)

    if has_concept(tokens, "fetch") and has_concept(tokens, "git"):
        return Plan(
            summary="Fetch latest git remote refs.",
            steps=[CommandStep(kind="command", command="git fetch --all --prune", description="Fetch all remotes and prune deleted branches.")],
            risk="low",
            requires_confirmation=False,
            source="template:git-fetch",
        )

    if "sync" in tokens and "origin" in tokens and "main" in tokens:
        return _simple_command_plan("Fetch origin and inspect sync state with origin/main.", "git fetch origin && git log --oneline --left-right --cherry-pick HEAD...origin/main", "template:git-sync-inspect", confirm=False)

    if "feature" in tokens and "branch" in tokens and has_concept(tokens, "make"):
        name = _extract_name(request, default="feature")
        safe = _safe_rel_path(name)
        if safe is None:
            return _unsafe_path_plan(name)
        return _simple_command_plan(f"Create feature branch {safe}.", f"git switch -c {shlex.quote(safe)}", "template:git-feature-branch", risk="medium", changes=True)

    if has_concept(tokens, "git") and "recent" in tokens and "commits" in tokens:
        return _simple_command_plan("Show recent git commits.", "git log --oneline --decorate --max-count=12", "template:git-log", confirm=False)

    if has_concept(tokens, "git") and "unstage" in tokens:
        return _simple_command_plan("Unstage all staged changes.", "git restore --staged .", "template:git-unstage", risk="medium", changes=True)

    if "undo" in tokens and "commit" in tokens:
        return _simple_command_plan("Undo the last commit while keeping changes.", "git reset --soft HEAD~1", "template:git-undo-soft", risk="medium", changes=True)

    if has_concept(tokens, "node") and "install" in tokens:
        return _simple_command_plan("Install Node dependencies with npm.", "npm install", "template:npm-install", risk="medium", changes=True)

    if "install" in tokens and ("dependencies" in tokens or "dependency" in tokens):
        package_plan = _package_install_plan(request)
        if package_plan:
            return package_plan

    if has_concept(tokens, "node") and has_concept(tokens, "test"):
        return _simple_command_plan("Run npm tests.", "npm test", "template:npm-test", confirm=False)

    if "npm" in tokens and "test" in tokens:
        return _simple_command_plan("Run npm tests.", "npm test", "template:npm-test", confirm=False)

    if "npm" in tokens and "install" in tokens:
        return _simple_command_plan("Install Node dependencies with npm.", "npm install", "template:npm-install", risk="medium", changes=True)

    if ("remove" in tokens or has_concept(tokens, "clean")):
        cleanup_plan = _cleanup_plan(request)
        if cleanup_plan:
            return cleanup_plan

    if "cargo" in tokens and has_concept(tokens, "build"):
        return _simple_command_plan("Build Rust project.", "cargo build", "template:cargo-build", risk="medium", changes=True)

    if "cargo" in tokens and has_concept(tokens, "test"):
        return _simple_command_plan("Run cargo tests.", "cargo test", "template:cargo-test", confirm=False)

    if has_concept(tokens, "build"):
        if Path("package.json").exists():
            return _simple_command_plan("Build the Node project.", "npm run build", "template:build", confirm=False)
        if Path("Cargo.toml").exists():
            return _simple_command_plan("Build the Rust project.", "cargo build", "template:build", confirm=False)
        if Path("CMakeLists.txt").exists():
            return _simple_command_plan("Build the CMake project.", "cmake --build build", "template:build", confirm=False)
        return _simple_command_plan("Compile Python files.", "python -m compileall -q .", "template:build", confirm=False)

    if has_concept(tokens, "clean") and has_concept(tokens, "build"):
        return _simple_command_plan("Clean generated build folders.", "rm -rf build dist", "template:clean-build", risk="medium", changes=True)

    if "cmake" in tokens and has_concept(tokens, "build"):
        return _simple_command_plan("Configure and build CMake project.", "cmake -S . -B build && cmake --build build", "template:cmake-build", risk="medium", changes=True)

    if "make" in tokens and "test" in tokens:
        return _simple_command_plan("Run make test.", "make test", "template:make-test", confirm=False)

    if "make" in tokens and "clean" in tokens:
        return _simple_command_plan("Run make clean.", "make clean", "template:make-clean", risk="medium", changes=True)

    if has_concept(tokens, "test") and ("run" in tokens or "starte" in text or "mach" in text or "mache" in text or "macke" in text):
        return _run_tests_plan(request)

    if (has_concept(tokens, "branch") and has_concept(tokens, "push")) or "origin main" in text or "fertig" in text:
        return _git_finish_plan(request)

    return None


def debug_match_report(request: str) -> str:
    """Return lightweight template-routing diagnostics for development."""
    tokens = tokenize(request)
    rows = [
        f"Debug match for: {request}",
        f"tokens: {tokens}",
    ]
    checks = [
        ("bash_script", ("script" in tokens or "skript" in tokens) and has_concept(tokens, "make"), "script plus create/make intent"),
        ("folder", bool(re.search(r"\b(?:make|create|mkdir|mache|macke|mach|erstelle|erstell)\s+(?:nested\s+)?(?:folder|directory|dir|ordner|verzeichnis)\s+\S+", request.lower())), "anchored verb + folder + target"),
        ("git_inspection", any(t in tokens for t in {"commit", "repo", "branch", "git"}) and any(t in tokens for t in {"summary", "summarize", "check", "ready", "log"}), "read-only git inspection language"),
        ("python_project", has_concept(tokens, "python") and has_concept(tokens, "project") and has_concept(tokens, "make"), "python project create intent"),
    ]
    for name, matched, reason in checks:
        confidence = "0.95" if matched else "0.00"
        rows.append(f"- {name}: matched={matched} confidence={confidence} reason={reason}")
    plan = plan_from_template(request)
    rows.append(f"selected: {plan.source if plan else '<none>'}")
    return "\n".join(rows)
