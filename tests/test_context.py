import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cairos.context import _compact_tree, _shallow_tree, collect_context, looks_like_project_root


class ContextScanTests(unittest.TestCase):
    def test_compact_tree_respects_max_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            for index in range(100):
                folder = root / f"dir{index}" / "sub"
                folder.mkdir(parents=True)
                (folder / f"file{index}.txt").write_text("x", encoding="utf-8")
            self.assertLessEqual(len(_compact_tree(root, max_entries=10, max_depth=5)), 10)

    def test_compact_tree_skips_ignored_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ["node_modules", ".venv", "AppData", "normal"]:
                (root / folder).mkdir()
            (root / "node_modules" / "huge.js").write_text("x", encoding="utf-8")
            (root / ".venv" / "x.py").write_text("x", encoding="utf-8")
            (root / "AppData" / "secret.txt").write_text("x", encoding="utf-8")
            (root / "normal" / "file.py").write_text("x", encoding="utf-8")
            paths = [item["path"] for item in _compact_tree(root, max_entries=20, max_depth=3)]
            self.assertIn("normal/", paths)
            self.assertIn("normal/file.py", paths)
            self.assertNotIn("node_modules/", paths)
            self.assertNotIn(".venv/", paths)
            self.assertNotIn("AppData/", paths)

    def test_home_directory_uses_shallow_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "deep" / "child").mkdir(parents=True)
            (root / "deep" / "child" / "file.txt").write_text("x", encoding="utf-8")
            old = Path.cwd()
            try:
                os.chdir(root)
                with patch("pathlib.Path.home", return_value=root):
                    context = collect_context(max_files=40)
            finally:
                os.chdir(old)
            paths = [item["path"] for item in context["files"]]
            self.assertIn("deep/", paths)
            self.assertNotIn("deep/child/", paths)
            self.assertEqual(context["file_tree_note"], "home directory: recursive file scan skipped")

    def test_non_project_directory_is_shallow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "deep" / "child").mkdir(parents=True)
            (root / "deep" / "child" / "file.txt").write_text("x", encoding="utf-8")
            old = Path.cwd()
            try:
                os.chdir(root)
                context = collect_context(max_files=40)
            finally:
                os.chdir(old)
            paths = [item["path"] for item in context["files"]]
            self.assertIn("deep/", paths)
            self.assertNotIn("deep/child/", paths)
            self.assertEqual(context["file_tree_note"], "non-project directory: recursive file scan limited")

    def test_project_root_collects_bounded_recursive_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("", encoding="utf-8")
            (root / "src" / "pkg").mkdir(parents=True)
            (root / "src" / "pkg" / "main.py").write_text("x", encoding="utf-8")
            old = Path.cwd()
            try:
                os.chdir(root)
                context = collect_context(max_files=40)
            finally:
                os.chdir(old)
            paths = [item["path"] for item in context["files"]]
            self.assertTrue(looks_like_project_root(root))
            self.assertIn("src/", paths)
            self.assertIn("src/pkg/", paths)
            self.assertIn("src/pkg/main.py", paths)
            self.assertEqual(context["file_tree_note"], "")

    def test_shallow_tree_handles_missing_path(self):
        self.assertEqual(_shallow_tree(Path("/definitely/not/here")), [])


if __name__ == "__main__":
    unittest.main()
