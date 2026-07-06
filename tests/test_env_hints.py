import unittest

from cairos.config import env_var_hint, shell_guess


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
        env = {"ComSpec": r"C:\Windows\System32\cmd.exe"}
        self.assertEqual(shell_guess(system="Windows", environ=env), "cmd")


if __name__ == "__main__":
    unittest.main()
