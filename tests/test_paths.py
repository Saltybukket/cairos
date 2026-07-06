import os
import unittest
from pathlib import Path
from unittest.mock import patch

from cairos.config import config_dir, state_dir


class PlatformPathTests(unittest.TestCase):
    def test_unix_paths(self):
        self.assertEqual(config_dir("Linux"), Path.home() / ".config" / "cairos")
        self.assertEqual(state_dir("Linux"), Path.home() / ".local" / "state" / "cairos")

    def test_windows_paths_use_appdata(self):
        env = {
            "APPDATA": r"C:\Users\Ada\AppData\Roaming",
            "LOCALAPPDATA": r"C:\Users\Ada\AppData\Local",
        }
        with patch.dict(os.environ, env):
            self.assertEqual(config_dir("Windows"), Path(env["APPDATA"]) / "cairos")
            self.assertEqual(state_dir("Windows"), Path(env["LOCALAPPDATA"]) / "cairos")


if __name__ == "__main__":
    unittest.main()
