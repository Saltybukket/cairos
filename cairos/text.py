"""Text normalization helpers for CAIROS.

This module keeps the deterministic planner useful even when the user writes
short, mixed German/English instructions or common typos such as ``macke``
instead of ``mache``.  The helpers intentionally stay lightweight and use only
Python's standard library so CAIROS remains easy to install as a small console
package.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

WORD_RE = re.compile(r"[a-zA-Z0-9_+./-]+")

UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

# Canonical concepts used by templates.  Add words here before reaching for AI.
CONCEPT_ALIASES: dict[str, set[str]] = {
    "make": {
        "make", "create", "new", "generate", "setup", "init", "initialize",
        "erstelle", "erstellen", "mach", "mache", "macke", "machst", "lege", "leg", "bau", "baue",
    },
    "folder": {"folder", "directory", "dir", "mkdir", "ordner", "verzeichnis"},
    "file": {"file", "datei", "touch"},
    "python": {"python", "py"},
    "cpp": {"cpp", "c++", "cplusplus", "cmake"},
    "c": {"c"},
    "node": {"node", "npm", "javascript", "js", "web"},
    "rust": {"rust", "cargo"},
    "build": {"build", "baue", "compile", "kompiliere"},
    "makefile": {"makefile"},
    "package": {"package", "paket"},
    "requirements": {"requirements", "requirements.txt"},
    "source": {"source", "src", "quelle"},
    "project": {"project", "projekt", "repo", "repository"},
    "header": {"header", "hpp", "h", "include"},
    "class": {"class", "klasse"},
    "venv": {"venv", "virtualenv", "environment", "umgebung"},
    "git": {"git", "repository", "repo"},
    "status": {"status", "zustand", "state"},
    "fetch": {"fetch", "hole", "hol", "pullen", "download"},
    "push": {"push", "pushe", "pushen", "hochladen"},
    "branch": {"branch", "zweig"},
    "main": {"main", "master"},
    "test": {"test", "tests", "testen", "pruefen", "prüfen"},
    "readme": {"readme", "documentation", "doku", "docu"},
    "gitignore": {"gitignore", ".gitignore"},
    "large": {"large", "big", "gross", "große", "grosse", "riesig"},
    "clean": {"clean", "cleanup", "remove", "delete", "loesche", "lösche", "entferne", "aufräumen", "aufraeumen"},
    "pycache": {"pycache", "__pycache__", "cache", "pythoncache"},
    "explain": {"explain", "erklaere", "erkläre", "was", "meaning"},
}

IGNORED_NAME_WORDS = set().union(*CONCEPT_ALIASES.values()) | {
    "with", "mit", "and", "und", "a", "an", "ein", "eine", "einen", "einem", "the", "for", "für", "fuer",
    "called", "named", "namens", "current", "aktuell", "aktuelle", "hier", "here", "in", "into", "at",
    "local", "lokal", "origin", "remote", "to", "zu", "auf", "fertig", "prepare", "ready",
}


def normalize_word(word: str) -> str:
    """Return a lowercase ASCII-ish representation of one word."""
    return word.lower().translate(UMLAUT_MAP)


def tokenize(text: str) -> list[str]:
    """Split text into normalized tokens while keeping simple path characters."""
    return [normalize_word(token) for token in WORD_RE.findall(text)]


def fuzzy_equal(a: str, b: str, cutoff: float = 0.78) -> bool:
    """Return True when two short words are close enough to count as equal."""
    a_norm = normalize_word(a)
    b_norm = normalize_word(b)
    if a_norm == b_norm:
        return True
    if len(a_norm) <= 2 or len(b_norm) <= 2:
        return False
    return SequenceMatcher(a=a_norm, b=b_norm).ratio() >= cutoff


def has_concept(tokens: list[str], concept: str, cutoff: float = 0.78) -> bool:
    """Check whether any token roughly matches an alias for a concept."""
    aliases = CONCEPT_ALIASES.get(concept, {concept})
    return any(any(fuzzy_equal(token, alias, cutoff=cutoff) for alias in aliases) for token in tokens)


def has_all(text: str, *concepts: str) -> bool:
    """Return True when all given concepts are present in a request."""
    tokens = tokenize(text)
    return all(has_concept(tokens, concept) for concept in concepts)


def has_any(text: str, *concepts: str) -> bool:
    """Return True when at least one concept is present in a request."""
    tokens = tokenize(text)
    return any(has_concept(tokens, concept) for concept in concepts)


def candidate_words(text: str) -> list[str]:
    """Return likely user-provided names by filtering command words."""
    words = WORD_RE.findall(text)
    candidates: list[str] = []
    for word in words:
        norm = normalize_word(word)
        if norm not in {normalize_word(w) for w in IGNORED_NAME_WORDS}:
            candidates.append(word)
    return candidates


SHELL_COMMAND_STARTS = {
    "git", "rm", "find", "chmod", "chown", "curl", "wget", "python", "python3",
    "pip", "npm", "cargo", "make", "cmake", "mkdir", "touch", "cp", "mv",
    "grep", "sed", "awk", "cat", "echo", "ls", "dd", "mkfs", "sudo",
}


def looks_like_shell_command(text: str) -> bool:
    """Heuristically decide whether text is a shell command, not a task."""
    stripped = text.strip()
    tokens = tokenize(stripped)
    if not tokens:
        return False
    if tokens[0] in SHELL_COMMAND_STARTS:
        return True
    if any(marker in stripped for marker in ["|", "&&", ";", ">", "<", "$(", "`"]):
        return True
    if any(token in {"-rf", "--force", "--hard", "-r"} for token in tokens):
        return True
    return False
