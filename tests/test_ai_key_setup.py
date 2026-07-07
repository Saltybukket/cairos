import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

from cairos.cli import main
from cairos.keys import setup_commands, validate_env_var_name


class AIKeySetupTests(unittest.TestCase):
    def run_cli(self, args, env=None):
        out = io.StringIO()
        err = io.StringIO()
        merged = {"HOME": tempfile.mkdtemp()}
        if env:
            merged.update(env)
        with patch.dict(os.environ, merged, clear=False):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_env_var_name_validation(self):
        for name in ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"]:
            ok, message = validate_env_var_name(name)
            self.assertTrue(ok, message)
        for name in ["my key", "sk-or-v1-fake-token-value", "AIzaFakeTokenValueForTestingOnly", "gsk_fake", "hf_fake"]:
            ok, _ = validate_env_var_name(name)
            self.assertFalse(ok)

    def test_cli_key_status_does_not_print_value(self):
        code, out, _ = self.run_cli(["config", "ai", "key", "status", "OPENROUTER_API_KEY"], {"OPENROUTER_API_KEY": "test-secret-value"})
        self.assertEqual(code, 0)
        self.assertIn("OPENROUTER_API_KEY: available", out)
        self.assertNotIn("test-secret-value", out)

    def test_cli_key_reveal_requires_explicit_yes_for_noninteractive(self):
        code, out, err = self.run_cli(["config", "ai", "key", "reveal", "OPENROUTER_API_KEY"], {"OPENROUTER_API_KEY": "test-secret-value"})
        self.assertEqual(code, 130)
        self.assertNotIn("test-secret-value", out)
        self.assertIn("without --yes", err)

    def test_cli_key_reveal_raw_yes_prints_only_value(self):
        code, out, _ = self.run_cli(["config", "ai", "key", "reveal", "OPENROUTER_API_KEY", "--raw", "--yes"], {"OPENROUTER_API_KEY": "test-secret-value"})
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "test-secret-value")

    def test_cli_key_commands_use_placeholder_by_default(self):
        code, out, _ = self.run_cli(["config", "ai", "key", "commands", "OPENROUTER_API_KEY", "--shell", "powershell"], {"OPENROUTER_API_KEY": "test-secret-value"})
        self.assertEqual(code, 0)
        self.assertIn("$env:OPENROUTER_API_KEY=\"your-key\"", out)
        self.assertNotIn("test-secret-value", out)

    def test_cli_key_commands_include_current_value_only_with_yes(self):
        code, out, _ = self.run_cli(
            ["config", "ai", "key", "commands", "OPENROUTER_API_KEY", "--shell", "bash", "--include-current-value", "--yes"],
            {"OPENROUTER_API_KEY": "test-secret-value"},
        )
        self.assertEqual(code, 0)
        self.assertIn("These commands contain your secret API key", out)
        self.assertIn("test-secret-value", out)

    def test_shell_command_variants(self):
        self.assertIn('export OPENROUTER_API_KEY="your-key"', "\n".join(setup_commands("OPENROUTER_API_KEY", shell="bash")))
        self.assertIn('$env:OPENROUTER_API_KEY="your-key"', "\n".join(setup_commands("OPENROUTER_API_KEY", shell="powershell")))
        self.assertIn("set OPENROUTER_API_KEY=your-key", "\n".join(setup_commands("OPENROUTER_API_KEY", shell="cmd")))


if __name__ == "__main__":
    unittest.main()
