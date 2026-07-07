import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
from unittest.mock import patch

from cairos.cli import main
from cairos.config import active_ai_profile_name, ai_fallback_settings, ai_profiles, configure_gemini, configure_openai
from cairos.gui import actions
from cairos.gui.security import mask_secret_text, same_origin, token_matches
from cairos.gui.server import check_gui_support, dependency_status
from cairos.gui.state import load_gui_state


def gui_deps_available() -> bool:
    return all(importlib.util.find_spec(name) is not None for name in ["fastapi", "uvicorn", "jinja2", "multipart"])


class GuiStateActionTests(unittest.TestCase):
    def with_home(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def test_load_gui_state_masks_key_availability(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home, "OPENROUTER_API_KEY": "sk-test-secret-value-that-must-not-render"}, clear=False):
            configure_openai("openrouter/free", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", profile="openrouter-free")
            state = load_gui_state()
        self.assertEqual(state.active_profile, "openrouter-free")
        self.assertTrue(state.profiles[0].key_available)
        self.assertNotIn("sk-test-secret", repr(state))

    def test_profile_creation_and_switching(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            result = actions.create_openrouter_free_profile()
            self.assertTrue(result.ok)
            result = actions.create_gemini_profile()
            self.assertTrue(result.ok)
            self.assertIn("openrouter-free", ai_profiles())
            self.assertIn("gemini-flash", ai_profiles())
            result = actions.switch_profile("openrouter-free")
            self.assertTrue(result.ok)
            self.assertEqual(active_ai_profile_name(), "openrouter-free")

    def test_fallback_toggle_and_order(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            actions.toggle_auto_fallback(False)
            actions.toggle_persist_switch(False)
            actions.set_fallback_order(["openrouter-free", "gemini-flash"])
            settings = ai_fallback_settings()
        self.assertFalse(settings["auto_fallback"])
        self.assertFalse(settings["fallback_persist_switch"])
        self.assertEqual(settings["fallback_order"], ["openrouter-free", "gemini-flash"])

    def test_backup_config_action(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            configure_openai("openrouter/free", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", profile="openrouter-free")
            result = actions.backup_config()
        self.assertTrue(result.ok)
        self.assertIn("backup", result.message.lower())

    def test_secret_masking_and_token_compare(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test-secret-value-that-must-not-render"}, clear=False):
            self.assertIn("<redacted>", mask_secret_text("value sk-test-secret-value-that-must-not-render"))
        self.assertIn("<redacted>", mask_secret_text("sk-or-v1-abcdefghijklmnopqrstuvwxyz"))
        self.assertIn("<redacted>", mask_secret_text("ghp_abcdefghijklmnopqrstuvwxyz123456"))
        self.assertIn("<redacted>", mask_secret_text("hf_abcdefghijklmnopqrstuvwxyz123456"))
        self.assertIn("ordinary-long-project-identifier", mask_secret_text("ordinary-long-project-identifier"))
        self.assertTrue(token_matches("abc", "abc"))
        self.assertFalse(token_matches("abc", "def"))

    def test_gui_check_reports_dependency_state(self):
        home = self.with_home()
        with patch.dict(os.environ, {"HOME": home}, clear=False):
            check = check_gui_support()
        self.assertIn("CAIROS GUI check:", "\n".join(check.lines))
        self.assertIn("Config readable:", "\n".join(check.lines))
        self.assertIn("python-multipart:", "\n".join(check.lines))

    def test_dependency_status_includes_form_parser(self):
        self.assertIn("python-multipart", dependency_status())

    def test_gui_check_cli_handles_missing_dependencies(self):
        out = io.StringIO()
        with patch("importlib.util.find_spec", return_value=None):
            with contextlib.redirect_stdout(out):
                code = main(["gui", "--check"])
        self.assertEqual(code, 1)
        self.assertIn("FastAPI: missing", out.getvalue())

    def test_non_local_gui_host_refused_even_for_check(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["gui", "--host", "0.0.0.0", "--check"])
        self.assertEqual(code, 1)
        self.assertIn("Refusing to bind", out.getvalue())

    def test_origin_helper(self):
        class Url:
            scheme = "http"
            hostname = "127.0.0.1"
            port = 5321

        self.assertTrue(same_origin(Url(), None))
        self.assertTrue(same_origin(Url(), "http://127.0.0.1:5321"))
        self.assertFalse(same_origin(Url(), "http://127.0.0.1:9999"))
        self.assertFalse(same_origin(Url(), "http://evil.example"))


@unittest.skipUnless(gui_deps_available(), "GUI optional dependencies are not installed")
class GuiRouteTests(unittest.TestCase):
    def with_home(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return temp.name

    def make_client(self, home):
        from fastapi.testclient import TestClient

        from cairos.gui.app import create_app

        with patch.dict(os.environ, {"HOME": home}, clear=False):
            app = create_app("test-token")
        return TestClient(app)

    def test_app_routes_and_partials(self):
        home = self.with_home()
        client = self.make_client(home)
        for path in ["/", "/partials/overview", "/partials/profiles", "/partials/provider-setup", "/partials/fallback", "/partials/doctor", "/partials/update"]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("sk-", response.text)
            self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_post_requires_token_and_origin(self):
        home = self.with_home()
        client = self.make_client(home)
        response = client.post("/profiles/switch", data={"profile_name": "missing"})
        self.assertEqual(response.status_code, 403)
        response = client.post("/profiles/switch", data={"token": "wrong", "profile_name": "missing"})
        self.assertEqual(response.status_code, 403)
        response = client.post(
            "/profiles/create/openrouter-free",
            data={"token": "test-token", "profile_name": "openrouter-free"},
            headers={"Origin": "http://evil.example"},
        )
        self.assertEqual(response.status_code, 403)

    def test_create_switch_and_backup_with_token(self):
        home = self.with_home()
        client = self.make_client(home)
        response = client.post(
            "/profiles/create/openrouter-free",
            data={"token": "test-token", "profile_name": "openrouter-free"},
            headers={"Origin": "http://testserver"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Created OpenRouter free profile", response.text)
        response = client.post("/profiles/switch", data={"token": "test-token", "profile_name": "openrouter-free"})
        self.assertEqual(response.status_code, 200)
        response = client.post("/config/backup", data={"token": "test-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("backup", response.text.lower())


if __name__ == "__main__":
    unittest.main()
