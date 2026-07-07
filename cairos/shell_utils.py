"""Shell/platform helpers for command templates and user guidance."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from .config import detect_shell_kind

TRAILING_SENTENCE_PUNCTUATION = ".,;:!?"
UNSAFE_SEARCH_CHARS_RE = re.compile(r"[;&|><`$(){}\n\r]")
FUZZY_FILLER_PATTERNS = [
    r"\bat\s+least\b",
    r"\b(?:it'?s|its)\s+named\b",
    r"\bcalled\s+something\s+like\b",
    r"\bnamed\s+something\s+like\b",
    r"\bsomething\s+like\s+that\b",
    r"\bor\s+something\b",
    r"\bprobably\b",
    r"\bmaybe\b",
    r"\bi\s+think\b",
    r"\bso\s+ahnlich\b",
    r"\bso\s+ähnlich\b",
    r"\birgendwie\b",
    r"\bheiss?t\s+ungefahr\b",
    r"\bheißt\s+ungefähr\b",
    r"\boder\s+so\b",
    r"\bglaube\s+ich\b",
]
STOP_WORDS = {
    "the", "a", "an", "directory", "folder", "dir", "into", "to", "go", "cd", "change",
    "cahnge", "find", "search", "named", "called", "something", "like", "that", "at",
    "least", "its", "it's", "current", "working", "shell", "parent", "please", "pls",
}


def shell_from_request(request: str, default: str | None = None) -> str:
    """Return cmd, powershell, posix or unknown, respecting explicit user hints."""
    text = request.lower()
    if any(phrase in text for phrase in ["windows cmd", "cmd.exe", "cmd shell", "in cmd"]):
        return "cmd"
    if any(phrase in text for phrase in ["powershell", "pwsh"]):
        return "powershell"
    if any(phrase in text for phrase in ["git bash", " wsl", "linux", "bash", "zsh", "fish", "macos", "mac os"]):
        return "posix"
    return default or detect_shell_kind()


def clean_target_name(value: str) -> str:
    """Remove sentence punctuation without stripping meaningful inner dots."""
    cleaned = value.strip().strip("\"'")
    while cleaned and cleaned[-1] in TRAILING_SENTENCE_PUNCTUATION:
        if cleaned[-1] == "." and re.search(r"\.[A-Za-z0-9]+$", cleaned):
            break
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def strip_fuzzy_fillers(value: str) -> str:
    """Remove uncertainty/filler language from a possible directory target."""
    cleaned = value
    cleaned = re.sub(r"\s+-\s+.*$", " ", cleaned)
    for pattern in FUZZY_FILLER_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return clean_target_name(cleaned)


def fuzzy_search_terms(value: str) -> list[str]:
    """Return safe useful terms for fuzzy directory search."""
    cleaned = strip_fuzzy_fillers(value)
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9_.-]+", cleaned):
        term = clean_target_name(term)
        if not term or term.lower() in STOP_WORDS or term.lower() == "something":
            continue
        terms.append(term)
    return terms


def extract_navigation_query(request: str) -> str:
    """Extract a likely directory query from navigation wording."""
    patterns = [
        r"(?:directory|folder|dir)\s+(.+?)(?:\s+mind\s+that|\s+using\s+|\s+from\s+here|$)",
        r"\b(?:go|cd|change|cahnge)\s+(?:into|to)\s+(?:the\s+)?(.+?)(?:\s+mind\s+that|\s+using\s+|\s+from\s+here|$)",
        r"\bfind\s+(?:the\s+)?(?:directory|folder|dir)\s+(.+?)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, request, flags=re.IGNORECASE)
        if match:
            return strip_fuzzy_fillers(match.group(1))
    return strip_fuzzy_fillers(request)


def is_safe_search_name(value: str) -> bool:
    return bool(value) and not UNSAFE_SEARCH_CHARS_RE.search(value)


def quote_for_shell(value: str, shell: str) -> str:
    """Quote a search term/path for the requested shell family."""
    if shell == "cmd":
        return f'"{value}"' if any(ch.isspace() for ch in value) else value
    if shell == "powershell":
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def quote_cli_arg(value: str) -> str:
    """Quote a CLI argument in a form that works for common shells."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def directory_search_command(name: str, shell: str, max_depth: int = 4) -> str:
    """Return a shell-appropriate bounded directory search command."""
    cleaned = strip_fuzzy_fillers(name)
    terms = fuzzy_search_terms(cleaned)
    if not terms:
        terms = [cleaned]
    if shell == "cmd":
        pattern = "*" + "*".join(terms) + "*"
        return f"dir /s /b /ad {pattern}"
    if shell == "powershell":
        if len(terms) > 1:
            escaped_terms = [term.replace("'", "''") for term in terms]
            checks = " -and ".join(f"$_.Name -like '*{term}*'" for term in escaped_terms)
            return (
                "Get-ChildItem -Path . -Directory -Recurse -ErrorAction SilentlyContinue | "
                f"Where-Object {{ {checks} }} | Select-Object -ExpandProperty FullName"
            )
        quoted = quote_for_shell(f"*{terms[0]}*", "powershell")
        return (
            f"Get-ChildItem -Path . -Directory -Recurse -Filter {quoted} "
            "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName"
        )
    if len(terms) > 1:
        predicates = " -o ".join(f"-iname {shlex.quote(f'*{term}*')}" for term in terms)
        return f"find . -maxdepth {max_depth} -type d \\( {predicates} \\) -print"
    quoted = shlex.quote(f"*{terms[0]}*")
    return f"find . -maxdepth {max_depth} -type d -iname {quoted} -print"


def cd_command_for_path(path: str, shell: str) -> str:
    """Return the command a parent shell wrapper/user should run."""
    if shell == "cmd":
        return f'cd /d "{path}"'
    if shell == "powershell":
        return f"Set-Location {quote_for_shell(path, 'powershell')}"
    return f"cd {shlex.quote(path)}"


def path_depth(path: Path, root: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return 999999
