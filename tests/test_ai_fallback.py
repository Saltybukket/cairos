import os
import tempfile
import unittest
from unittest.mock import patch

from cairos.ai.base import AIPlannerError, AiFailure, plan_with_ai_fallback
from cairos.config import active_ai_profile_name, configure_gemini, configure_openai, load_config, save_config
from cairos.models import CommandStep, Plan
from cairos.planner import make_plan


def write_plan() -> Plan:
    return Plan(
        summary="AI fallback plan",
        source="ai",
        steps=[
            CommandStep(
                kind="write_file",
                path="result.txt",
                content="ok\n",
                description="Write result.",
                changes_files=True,
                risk="medium",
            )
        ],
        risk="medium",
        requires_confirmation=True,
    )


def failure(profile: str, status_code: int, category: str) -> AIPlannerError:
    return AIPlannerError(
        f"{profile} failed",
        failure=AiFailure(
            profile=profile,
            provider="gemini",
            model="gemini-2.5-flash",
            endpoint="https://generativelanguage.googleapis.com/v1beta",
            status_code=status_code,
            category=category,
            message=f"{profile} failed",
            recoverable=True,
        ),
    )


class AIFallbackTests(unittest.TestCase):
    def configure_profiles(self) -> str:
        home = tempfile.mkdtemp()
        env = {
            "HOME": home,
            "GEMINI_API_KEY": "test-gemini-key",
            "OPENROUTER_API_KEY": "test-openrouter-key",
        }
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        configure_openai(
            model="openrouter/free",
            api_key_env="OPENROUTER_API_KEY",
            endpoint="https://openrouter.ai/api/v1",
            profile="openrouter-free",
        )
        configure_gemini(model="gemini-2.5-flash", api_key_env="GEMINI_API_KEY", profile="gemini-flash")
        return home

    def test_429_falls_back_and_persists_active_profile(self):
        self.configure_profiles()
        with patch("cairos.ai.base._gemini_plan", side_effect=failure("gemini-flash", 429, "rate_limit_quota")):
            with patch("cairos.ai.base._openai_compatible_plan", return_value=write_plan()):
                plan = plan_with_ai_fallback("do a complex task")
        self.assertEqual(plan.source, "ai")
        self.assertEqual(active_ai_profile_name(), "openrouter-free")
        self.assertIn("AI profile fallback", "\n".join(plan.notices))
        self.assertIn("Switched to openrouter-free", "\n".join(plan.notices))

    def test_402_falls_back_from_paid_profile(self):
        self.configure_profiles()
        with patch("cairos.ai.base._gemini_plan", side_effect=failure("gemini-flash", 402, "insufficient_credits")):
            with patch("cairos.ai.base._openai_compatible_plan", return_value=write_plan()):
                plan = plan_with_ai_fallback("do a complex task")
        self.assertIn("402", "\n".join(plan.notices))
        self.assertEqual(active_ai_profile_name(), "openrouter-free")

    def test_missing_key_profile_is_skipped(self):
        home = tempfile.mkdtemp()
        with patch.dict(os.environ, {"HOME": home, "OPENROUTER_API_KEY": "test-openrouter-key"}, clear=False):
            configure_openai(
                model="openrouter/free",
                api_key_env="OPENROUTER_API_KEY",
                endpoint="https://openrouter.ai/api/v1",
                profile="openrouter-free",
            )
            configure_gemini(model="gemini-2.5-flash", api_key_env="GEMINI_API_KEY", profile="gemini-flash")
            with patch("cairos.ai.base._gemini_plan") as gemini:
                with patch("cairos.ai.base._openai_compatible_plan", return_value=write_plan()):
                    plan = plan_with_ai_fallback("do a complex task")
        gemini.assert_not_called()
        self.assertEqual(plan.source, "ai")
        self.assertIn("missing_key", "\n".join(plan.notices))

    def test_all_profiles_fail_reports_tried_profiles(self):
        self.configure_profiles()
        with patch("cairos.ai.base._gemini_plan", side_effect=failure("gemini-flash", 429, "rate_limit_quota")):
            with patch("cairos.ai.base._openai_compatible_plan", side_effect=failure("openrouter-free", 503, "temporary_provider")):
                with self.assertRaises(AIPlannerError) as caught:
                    plan_with_ai_fallback("do a complex task")
        message = str(caught.exception)
        self.assertIn("All configured AI profiles failed", message)
        self.assertIn("gemini-flash", message)
        self.assertIn("openrouter-free", message)

    def test_disabled_fallback_does_not_try_other_profiles(self):
        self.configure_profiles()
        config = load_config()
        config["ai"]["auto_fallback"] = False
        save_config(config)
        with patch("cairos.ai.base._gemini_plan", side_effect=failure("gemini-flash", 429, "rate_limit_quota")):
            with patch("cairos.ai.base._openai_compatible_plan") as openai:
                with self.assertRaises(AIPlannerError):
                    plan_with_ai_fallback("do a complex task")
        openai.assert_not_called()

    def test_planner_keeps_confirmation_on_ai_fallback_write_plan(self):
        self.configure_profiles()
        with patch("cairos.ai.base._gemini_plan", side_effect=failure("gemini-flash", 429, "rate_limit_quota")):
            with patch("cairos.ai.base._openai_compatible_plan", return_value=write_plan()):
                plan = make_plan("setup this repo for a clean release")
        self.assertEqual(plan.source, "ai")
        self.assertTrue(plan.requires_confirmation)
        self.assertIn("AI profile fallback", "\n".join(plan.notices))

    def test_reliable_template_does_not_call_ai(self):
        self.configure_profiles()
        with patch("cairos.ai.base._gemini_plan") as gemini:
            plan = make_plan("create folder docs")
        gemini.assert_not_called()
        self.assertNotEqual(plan.source, "ai")


if __name__ == "__main__":
    unittest.main()
