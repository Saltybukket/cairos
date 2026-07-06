import unittest

from cairos.config import detect_shell_kind, env_var_hint, env_var_setup_hint, shell_guess


class EnvHintTests(unittest.TestCase):
    def test_posix_hint(self):
        self.assertEqual(env_var_hint("GEMINI_API_KEY", "zsh"), ['export GEMINI_API_KEY="your-key"'])

    def test_powershell_hint(self):
        hint = "\n".join(env_var_hint("GEMINI_API_KEY", "powershell"))
        self.assertIn('$env:GEMINI_API_KEY="your-key"', hint)
        self.assertIn('[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-key", "User")', hint)

    def test_cmd_hint(self):
        hint = "\n".join(env_var_hint("GEMINI_API_KEY", "cmd"))
        self.assertIn("set GEMINI_API_KEY=your-key", hint)
        self.assertIn('setx GEMINI_API_KEY "your-key"', hint)

    def test_shell_guess_windows_cmd(self):
        env = {"ComSpec": r"C:\Windows\System32\cmd.exe", "PSModulePath": "present"}
        self.assertEqual(shell_guess(system="Windows", environ=env), "cmd")

    def test_env_override(self):
        self.assertEqual(detect_shell_kind(environ={"CAIROS_SHELL": "cmd"}), "cmd")
        self.assertEqual(detect_shell_kind(environ={"CAIROS_SHELL": "powershell"}), "powershell")
        self.assertEqual(detect_shell_kind(environ={"CAIROS_SHELL": "bash"}), "posix")

    def test_setup_hint_cmd(self):
        hint = env_var_setup_hint("OPENAI_API_KEY", shell_kind="cmd")
        self.assertIn("For this cmd.exe session:", hint)
        self.assertIn("set OPENAI_API_KEY=your-key", hint)
        self.assertIn('setx OPENAI_API_KEY "your-key"', hint)

    def test_setup_hint_powershell(self):
        hint = env_var_setup_hint("OPENAI_API_KEY", shell_kind="powershell")
        self.assertIn("For this PowerShell session:", hint)
        self.assertIn('$env:OPENAI_API_KEY="your-key"', hint)
        self.assertIn('[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key", "User")', hint)

    def test_setup_hint_posix(self):
        hint = env_var_setup_hint("OPENAI_API_KEY", shell_kind="posix")
        self.assertIn("For this shell session:", hint)
        self.assertIn('export OPENAI_API_KEY="your-key"', hint)

    def test_setup_hint_unknown_windows(self):
        hint = env_var_setup_hint("OPENAI_API_KEY", shell_kind="unknown-windows")
        self.assertIn("For cmd.exe:", hint)
        self.assertIn("For PowerShell:", hint)


if __name__ == "__main__":
    unittest.main()
