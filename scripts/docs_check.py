"""Lightweight documentation consistency checks for release prep."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> int:
    print(message)
    return 1


def check_readme_links() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((docs/[^)]+\.md|CHANGELOG\.md)\)", readme)
    missing = [link for link in links if not (ROOT / link).exists()]
    if missing:
        return fail("Missing README links:\n" + "\n".join(f"- {link}" for link in missing))
    return 0


def check_version_strings() -> int:
    init_text = (ROOT / "cairos" / "__init__.py").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    init_match = re.search(r'__version__ = "([^"]+)"', init_text)
    project_match = re.search(r'^version = "([^"]+)"', pyproject, flags=re.MULTILINE)
    if not init_match or not project_match or init_match.group(1) != project_match.group(1):
        return fail("Version mismatch between pyproject.toml and cairos/__init__.py")
    version = init_match.group(1)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version}" not in changelog:
        return fail(f"CHANGELOG.md does not contain section for {version}")
    stale = []
    for base in [ROOT / "README.md", ROOT / "docs", ROOT / "tests" / "cases" / "testcases.json"]:
        files = [base] if base.is_file() else list(base.rglob("*.md"))
        for file in files:
            text = file.read_text(encoding="utf-8")
            if "0.5.0a2" in text:
                stale.append(str(file.relative_to(ROOT)))
    if stale:
        return fail("Obsolete 0.5.0a2 references:\n" + "\n".join(f"- {item}" for item in stale))
    return 0


def main() -> int:
    for check in [check_readme_links, check_version_strings]:
        code = check()
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
