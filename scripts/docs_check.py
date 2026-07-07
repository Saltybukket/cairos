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


def check_publishing_files() -> int:
    publish = ROOT / ".github" / "workflows" / "publish.yml"
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    manifest = ROOT / "MANIFEST.in"
    missing = [str(path.relative_to(ROOT)) for path in [publish, ci, manifest] if not path.exists()]
    if missing:
        return fail("Missing publishing files:\n" + "\n".join(f"- {item}" for item in missing))
    text = publish.read_text(encoding="utf-8")
    required = [
        "release:",
        "workflow_dispatch:",
        "id-token: write",
        "name: pypi",
        "pypa/gh-action-pypi-publish@release/v1",
    ]
    absent = [item for item in required if item not in text]
    if absent:
        return fail("publish.yml is missing Trusted Publishing markers:\n" + "\n".join(f"- {item}" for item in absent))
    forbidden = ["password:", "api-token:", "__token__"]
    present = [item for item in forbidden if item in text]
    if present:
        return fail("publish.yml must not contain token/password settings:\n" + "\n".join(f"- {item}" for item in present))
    return 0


def main() -> int:
    for check in [check_readme_links, check_version_strings, check_publishing_files]:
        code = check()
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
