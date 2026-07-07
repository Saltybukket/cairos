import re
import subprocess
import unittest
from pathlib import Path

import cairos


ROOT = Path(__file__).resolve().parents[1]


class ReleasePolishTests(unittest.TestCase):
    def test_version_consistency(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', pyproject, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), cairos.__version__)
        self.assertIn(f"## {cairos.__version__}", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        proc = subprocess.run(["python3", "-m", "cairos.cli", "--version"], cwd=ROOT, text=True, capture_output=True, check=True)
        self.assertEqual(proc.stdout.strip(), cairos.__version__)

    def test_publish_workflow_uses_trusted_publishing(self):
        workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("id-token: write", workflow)
        self.assertIn("name: pypi", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)
        self.assertNotIn("password:", workflow)
        self.assertNotIn("api-token:", workflow)

    def test_package_metadata_is_pypi_ready(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "cairos-shell"', pyproject)
        self.assertIn('cairos = "cairos.cli:main"', pyproject)
        self.assertIn('Repository = "https://github.com/Saltybukket/cairos"', pyproject)
        self.assertIn('Changelog = "https://github.com/Saltybukket/cairos/blob/main/CHANGELOG.md"', pyproject)
        self.assertIn('"python-multipart"', pyproject)

    def test_readme_doc_links_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\((docs/[^)]+\.md|CHANGELOG\.md)\)", readme)
        self.assertGreater(len(links), 5)
        missing = [link for link in links if not (ROOT / link).exists()]
        self.assertEqual(missing, [])

    def test_no_obsolete_version_in_docs(self):
        stale = []
        for path in [ROOT / "README.md", ROOT / "docs", ROOT / "tests" / "cases" / "testcases.json"]:
            files = [path] if path.is_file() else list(path.rglob("*.md"))
            for file in files:
                if "0.5.0a2" in file.read_text(encoding="utf-8"):
                    stale.append(str(file.relative_to(ROOT)))
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
