import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cairos.cli import main


class CLIReleaseTests(unittest.TestCase):
    def run_cli(self, args, home=None):
        out = io.StringIO()
        err = io.StringIO()
        env = {"HOME": home or tempfile.mkdtemp()}
        with patch.dict(os.environ, env, clear=False):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_openrouter_shortcut_and_examples(self):
        home = tempfile.mkdtemp()
        code, out, _ = self.run_cli(["config", "ai", "use-openrouter-free"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("openrouter/free", out)
        self.assertIn("OPENROUTER_API_KEY", out)
        code, out, _ = self.run_cli(["ai", "examples"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("OpenRouter free", out)
        self.assertIn("Groq", out)

    def test_update_and_backup_config(self):
        home = tempfile.mkdtemp()
        self.run_cli(["config", "ai", "use-openrouter-free"], home=home)
        code, out, _ = self.run_cli(["update"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("Your config will be preserved", out)
        self.assertIn("Raw API keys are not stored", out)
        code, out, _ = self.run_cli(["backup-config"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("Config backup created", out)

    def test_ai_doctor_help(self):
        code, out, _ = self.run_cli(["config", "ai", "doctor"])
        self.assertEqual(code, 0)
        self.assertIn("HTTP guidance", out)
        self.assertIn("auto fallback", out)
        code, out, _ = self.run_cli(["config", "ai", "--help"])
        self.assertEqual(code, 0)
        self.assertIn("use-openrouter-free", out)

    def test_ai_fallback_cli(self):
        home = tempfile.mkdtemp()
        code, out, _ = self.run_cli(["config", "ai", "fallback", "status"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("AI fallback", out)
        self.assertIn("enabled", out)
        code, out, _ = self.run_cli(["config", "ai", "fallback", "disable"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("disabled", out)
        code, out, _ = self.run_cli(["config", "ai", "fallback", "order", "openrouter-free", "gemini-flash"], home=home)
        self.assertEqual(code, 0)
        self.assertIn("openrouter-free, gemini-flash", out)

    def test_find_dir_fuzzy_multi_word(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "oop-project-ss26"
            target.mkdir()
            old = os.getcwd()
            try:
                os.chdir(root)
                code, out, err = self.run_cli(["find-dir", "oop ss26"], home=tempfile.mkdtemp())
            finally:
                os.chdir(old)
            self.assertEqual(code, 0, err)
            self.assertIn("oop-project-ss26", out)

    def test_run_navigation_prints_matches_and_cd_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "oop-project-ss26"
            target.mkdir()
            old = os.getcwd()
            try:
                os.chdir(root)
                code, out, err = self.run_cli(
                    ["run", "change", "into", "the", "directory", "oop", "ss26", "at", "least", "its", "named", "something", "like", "that", "--yes"],
                    home=tempfile.mkdtemp(),
                )
            finally:
                os.chdir(old)
            self.assertEqual(code, 0, err)
            self.assertIn("Matches:", out)
            self.assertIn("oop-project-ss26", out)
            self.assertIn("Copy-paste command:", out)
            self.assertIn("cannot permanently change", out)


if __name__ == "__main__":
    unittest.main()
