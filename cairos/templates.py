import re
from .models import Plan

_PROJECT_NAME_RE = r"[a-zA-Z][a-zA-Z0-9_-]*"


def _extract_name(text: str, default: str = "demo") -> str:
    text = text.strip()
    patterns = [
        rf"(?:project|projekt)\s+({_PROJECT_NAME_RE})",
        rf"(?:called|named|namens)\s+({_PROJECT_NAME_RE})",
        rf"(?:python|cpp|c\+\+|cmake)\s+(?:project|projekt)\s+({_PROJECT_NAME_RE})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    words = re.findall(_PROJECT_NAME_RE, text)
    ignored = {"create", "make", "new", "python", "project", "projekt", "with", "venv", "git", "and", "a", "an", "ein", "eine", "erstelle", "mach", "mache", "cpp", "cmake"}
    candidates = [w for w in words if w.lower() not in ignored]
    return candidates[-1] if candidates else default


def plan_from_template(request: str) -> Plan | None:
    text = request.strip().lower()

    if any(key in text for key in ["python project", "python projekt", "create python", "new python", "erstelle python", "mach python"]):
        name = _extract_name(request)
        return Plan(
            summary=f"Create a Python project named {name}.",
            commands=[
                f"mkdir -p {name}",
                f"cd {name}",
                "python3 -m venv .venv",
                "touch main.py requirements.txt README.md",
                "printf '.venv/\\n__pycache__/\\n*.pyc\\n' > .gitignore",
                "git init",
            ],
            risk="low",
            notes=["Creates a local project folder and initializes git."],
        )

    if any(key in text for key in ["setup venv", "create venv", "venv here", "python venv"]):
        return Plan(
            summary="Create a Python virtual environment in the current directory.",
            commands=["python3 -m venv .venv"],
            risk="low",
            notes=["Activate it with: source .venv/bin/activate"],
        )

    if any(key in text for key in ["git init", "initialize git", "init git"]):
        return Plan(
            summary="Initialize a git repository in the current directory.",
            commands=["git init"],
            risk="low",
        )

    if any(key in text for key in ["find large files", "large files", "big files", "große dateien"]):
        return Plan(
            summary="Find large files below the current directory.",
            commands=["find . -type f -size +100M -print"],
            risk="low",
        )

    if any(key in text for key in ["clean python cache", "remove pycache", "clean pycache"]):
        return Plan(
            summary="Remove Python bytecode cache folders.",
            commands=["find . -type d -name __pycache__ -prune -exec rm -rf {} +"],
            risk="medium",
            notes=["This removes generated Python cache folders only."],
        )

    return None
