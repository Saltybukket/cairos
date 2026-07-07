import os
import tempfile
import unittest
from unittest.mock import patch

from cairos.models import Plan
from cairos.planner import make_plan


class PlannerRoutingTests(unittest.TestCase):
    def test_uncertain_template_uses_ai_when_available(self):
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home, "OPENROUTER_API_KEY": "test-key"}
            with patch.dict(os.environ, env, clear=False):
                from cairos.config import configure_openai

                configure_openai(
                    model="openrouter/free",
                    api_key_env="OPENROUTER_API_KEY",
                    endpoint="https://openrouter.ai/api/v1",
                    profile="openrouter-free",
                )
                with patch("cairos.planner.plan_with_ai_fallback", return_value=Plan(summary="AI plan", source="ai")):
                    plan = make_plan("setup this repo for a clean release")
        self.assertEqual(plan.source, "ai")

    def test_uncertain_template_no_ai_returns_no_reliable_match(self):
        with tempfile.TemporaryDirectory() as home:
            with patch.dict(os.environ, {"HOME": home}, clear=False):
                plan = make_plan("setup this repo for a clean release")
        self.assertEqual(plan.source, "none")
        self.assertIn("No reliable deterministic template matched", plan.summary)


if __name__ == "__main__":
    unittest.main()
