from __future__ import annotations

import re
from pathlib import Path
from .models import CommandStep, Plan, VerificationStep
from .rules import load_rules

_PROJECT_NAME_RE = r"[a-zA-Z][a-zA-Z0-9_-]*"
_CLASS_NAME_RE = r"[A-Z][a-zA-Z0-9_]*"

IGNORED_NAME_WORDS = {
    "create", "make", "new", "python", "project", "projekt", "with", "venv", "git", "and", "a", "an",
    "ein", "eine", "erstelle", "mach", "mache", "cpp", "cmake", "folder", "directory", "ordner",
    "file", "datei", "header", "class", "klasse", "for", "für", "called", "named", "namens",
}


def _extract_name(text: str, default: str = "demo") -> str:
    text = text.strip()
    patterns = [
        rf"(?:project|projekt|folder|directory|ordner)\s+({_PROJECT_NAME_RE})",
        rf"(?:called|named|namens)\s+({_PROJECT_NAME_RE})",
        rf"(?:python|cpp|c\+\+|cmake)\s+(?:project|projekt)\s+({_PROJECT_NAME_RE})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    words = re.findall(_PROJECT_NAME_RE, text)
    candidates = [w for w in words if w.lower() not in IGNORED_NAME_WORDS]
    return candidates[-1] if candidates else default


def _extract_path_after_keywords(text: str, keywords: list[str], default: str) -> str:
    for keyword in keywords:
        match = re.search(rf"\b{re.escape(keyword)}\s+([^\s]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return default


def _extract_class_name(text: str, default: str = "Demo") -> str:
    patterns = [
        rf"(?:class|klasse)\s+({_CLASS_NAME_RE})",
        rf"(?:header|file|datei)\s+({_CLASS_NAME_RE})",
        rf"\b({_CLASS_NAME_RE})\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            name = match.group(1)
            if name.lower() not in IGNORED_NAME_WORDS:
                return name[:1].upper() + name[1:]
    return default


def _header_guard(class_name: str, extension: str) -> str:
    raw = f"{class_name}{extension}".upper()
    return re.sub(r"[^A-Z0-9]", "_", raw)


def _cpp_header_content(class_name: str, namespace: str = "", extension: str = ".hpp") -> str:
    guard = _header_guard(class_name, extension)
    body = f"""#ifndef {guard}
#define {guard}

class {class_name} {{
public:
    {class_name}();
    {class_name}(const {class_name}& other);
    {class_name}({class_name}&& other) noexcept;
    {class_name}& operator=(const {class_name}& other);
    {class_name}& operator=({class_name}&& other) noexcept;
    ~{class_name}();

private:
}};

#endif // {guard}
"""
    if namespace:
        body = f"""#ifndef {guard}
#define {guard}

namespace {namespace} {{

class {class_name} {{
public:
    {class_name}();
    {class_name}(const {class_name}& other);
    {class_name}({class_name}&& other) noexcept;
    {class_name}& operator=(const {class_name}& other);
    {class_name}& operator=({class_name}&& other) noexcept;
    ~{class_name}();

private:
}};

}} // namespace {namespace}

#endif // {guard}
"""
    return body


def _python_project_plan(request: str) -> Plan:
    name = _extract_name(request)
    package = name.replace("-", "_")
    use_pytest = "pytest" in request.lower()
    steps = [
        CommandStep(kind="mkdir", path=name, description="Create the project root directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/{package}", description="Create the Python package directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/tests", description="Create the test directory.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/{package}/__init__.py", content="__version__ = \"0.1.0\"\n", description="Create package initializer.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/.gitignore", content=".venv/\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\nbuild/\ndist/\n", description="Create Python .gitignore.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/pyproject.toml", content=f"[project]\nname = \"{name}\"\nversion = \"0.1.0\"\nrequires-python = \">=3.10\"\n\n", description="Create minimal pyproject.toml.", changes_files=True),
    ]
    if use_pytest:
        steps.append(CommandStep(kind="write_file", path=f"{name}/tests/test_basic.py", content="def test_basic():\n    assert True\n", description="Create a basic pytest test.", changes_files=True))
    if "venv" in request.lower():
        steps.append(CommandStep(kind="command", command=f"cd {name} && python3 -m venv .venv", description="Create a Python virtual environment.", changes_files=True))
    if "git" in request.lower():
        steps.append(CommandStep(kind="command", command=f"cd {name} && git init", description="Initialize git repository.", changes_files=True))
    return Plan(
        summary=f"Create a Python project named {name}.",
        steps=steps,
        risk="low",
        notes=["Activate the venv with: source .venv/bin/activate" if "venv" in request.lower() else "No venv requested."],
        verification=[VerificationStep(kind="dir_exists", target=name), VerificationStep(kind="file_exists", target=f"{name}/pyproject.toml")],
        source="template",
    )


def _cpp_project_plan(request: str) -> Plan:
    rules = load_rules()["cpp"]
    name = _extract_name(request)
    include_dir = rules.get("include_dir", "include")
    source_dir = rules.get("source_dir", "src")
    test_dir = rules.get("test_dir", "tests")
    cmake = f"""cmake_minimum_required(VERSION 3.16)
project({name})

set(CMAKE_CXX_STANDARD 17)
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
        source="template",
    )


def _cpp_header_plan(request: str) -> Plan:
    rules = load_rules()["cpp"]
    class_name = _extract_class_name(request)
    include_dir = rules.get("include_dir", "include")
    extension = rules.get("header_extension", ".hpp")
    namespace = rules.get("namespace", "")
    path = _extract_path_after_keywords(request, ["at", "in", "into"], f"{include_dir}/{class_name}{extension}")
    if not Path(path).suffix:
        path = str(Path(path) / f"{class_name}{extension}")
    return Plan(
        summary=f"Create C++ header for class {class_name}.",
        steps=[
            CommandStep(kind="mkdir", path=str(Path(path).parent), description="Create header parent directory.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=_cpp_header_content(class_name, namespace, extension), description=f"Write header with ifndef guard and class {class_name}.", changes_files=True),
        ],
        risk="low",
        notes=["Header style comes from CAIROS rules: cpp.header_style=ifndef."],
        verification=[VerificationStep(kind="file_exists", target=path)],
        source="template",
    )


def _git_finish_plan(_: str) -> Plan:
    return Plan(
        summary="Safely prepare the current branch before pushing.",
        steps=[
            CommandStep(kind="command", command="git status --short", description="Inspect uncommitted local changes.", risk="low"),
            CommandStep(kind="command", command="git branch --show-current", description="Print the current branch.", risk="low"),
            CommandStep(kind="command", command="git fetch origin", description="Fetch latest remote refs without merging.", risk="low"),
            CommandStep(kind="command", command="git log --oneline --decorate --graph --max-count=10 --all", description="Show recent local and remote commit graph.", risk="low"),
        ],
        risk="medium",
        notes=[
            "This workflow intentionally does not merge or push automatically.",
            "After reviewing the output, run a merge/rebase/push explicitly or ask CAIROS for the next step.",
        ],
        source="template:git-safe-workflow",
        requires_confirmation=False,
    )


def plan_from_template(request: str) -> Plan | None:
    text = request.strip().lower()

    if any(key in text for key in ["python project", "python projekt", "create python", "new python", "erstelle python", "mach python"]):
        return _python_project_plan(request)

    if any(key in text for key in ["header file", "header datei", "hpp", "c++ header", "cpp header"]):
        return _cpp_header_plan(request)

    if any(key in text for key in ["cpp project", "c++ project", "cmake project", "create cpp project", "create c++ project"]):
        return _cpp_project_plan(request)

    if any(key in text for key in ["setup venv", "create venv", "venv here", "python venv"]):
        return Plan(
            summary="Create a Python virtual environment in the current directory.",
            steps=[CommandStep(kind="command", command="python3 -m venv .venv", description="Create .venv.", changes_files=True)],
            risk="low",
            notes=["Activate it with: source .venv/bin/activate"],
            verification=[VerificationStep(kind="dir_exists", target=".venv")],
        )

    if any(key in text for key in ["git init", "initialize git", "init git"]):
        return Plan(
            summary="Initialize a git repository in the current directory.",
            steps=[CommandStep(kind="command", command="git init", description="Initialize git.", changes_files=True)],
            risk="low",
        )

    if any(key in text for key in ["create folder", "make folder", "new folder", "mkdir", "ordner erstellen", "erstelle ordner"]):
        name = _extract_name(request)
        return Plan(
            summary=f"Create folder {name}.",
            steps=[CommandStep(kind="mkdir", path=name, description=f"Create directory {name}.", changes_files=True)],
            risk="low",
            verification=[VerificationStep(kind="dir_exists", target=name)],
        )

    if any(key in text for key in ["create file", "touch file", "erstelle datei", "make file"]):
        path = _extract_path_after_keywords(request, ["file", "datei"], "new_file.txt")
        return Plan(
            summary=f"Create empty file {path}.",
            steps=[CommandStep(kind="write_file", path=path, content="", description=f"Create empty file {path}.", changes_files=True)],
            risk="low",
            verification=[VerificationStep(kind="file_exists", target=path)],
        )

    if any(key in text for key in ["find large files", "large files", "big files", "große dateien"]):
        return Plan(
            summary="Find large files below the current directory.",
            steps=[CommandStep(kind="command", command="find . -type f -size +100M -print", description="List files larger than 100 MB.")],
            risk="low",
            requires_confirmation=False,
        )

    if any(key in text for key in ["clean python cache", "remove pycache", "clean pycache"]):
        return Plan(
            summary="Remove Python bytecode cache folders.",
            steps=[CommandStep(kind="command", command="find . -type d -name __pycache__ -prune -exec rm -rf {} +", description="Delete generated __pycache__ folders only.", changes_files=True, risk="medium")],
            risk="medium",
            notes=["This removes generated Python cache folders only."],
        )

    if any(key in text for key in ["finish current branch", "prepare push", "ready for origin main", "branch fertig", "push to origin main"]):
        return _git_finish_plan(request)

    return None
