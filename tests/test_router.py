import unittest
from unittest.mock import patch

from cairos.router import ROUTE_AI, ROUTE_CONVERSATION, ROUTE_NO_MATCH, ROUTE_SAFETY_CHECK, ROUTE_TEMPLATE, classify_request_complexity, format_route_debug, route_request, score_template_candidate
from cairos.templates import plan_from_template


class RouterTests(unittest.TestCase):
    def test_route_request_common_routes(self):
        self.assertEqual(route_request("create folder docs", allow_ml=False).route, ROUTE_TEMPLATE)
        self.assertEqual(route_request("how are you", allow_ml=False).route, ROUTE_CONVERSATION)
        self.assertEqual(route_request("rm -rf /", allow_ml=False).route, ROUTE_SAFETY_CHECK)
        self.assertEqual(route_request("setup this whole repo for release and fix docs", allow_ml=False).route, ROUTE_AI)
        self.assertEqual(route_request("flibbertigibbet xyzzy", allow_ml=False).route, ROUTE_NO_MATCH)

    def test_ml_router_missing_model_falls_back(self):
        with patch("cairos.router._model_paths", return_value=[]):
            decision = route_request("create folder docs", allow_ml=True, router="ml")
        self.assertEqual(decision.route, ROUTE_TEMPLATE)
        self.assertIn("fallback", str(decision.debug.get("router_type", "")))

    def test_complex_directory_still_extracts_good_terms(self):
        request = "change into the directory oop ss26 at least its named something like that - change the current directory"
        plan = plan_from_template(request)
        decision = score_template_candidate(request, plan, classify_request_complexity(request))
        self.assertEqual(decision.candidate_source, "template:cd-guidance")
        self.assertIn("oop", decision.matched_terms)
        self.assertIn("ss26", decision.matched_terms)
        self.assertNotIn("something", decision.matched_terms)
        self.assertNotIn("current", decision.matched_terms)
        self.assertGreaterEqual(decision.confidence, 0.8)

    def test_broad_repo_setup_is_not_template_confident(self):
        request = "setup this repo for a clean release"
        plan = plan_from_template(request)
        decision = score_template_candidate(request, plan, classify_request_complexity(request))
        self.assertIn(decision.route, {"ai", "no_match"})
        self.assertLess(decision.confidence, 0.8)

    def test_simple_template_steps_back_for_compound_creation(self):
        request = "create a folder called demo with a main.py and a readme"
        plan = plan_from_template(request)
        decision = score_template_candidate(request, plan, classify_request_complexity(request))
        self.assertIn(decision.route, {"ai", "no_match"})
        self.assertLess(decision.confidence, 0.8)

    def test_python_project_template_steps_back_for_open_ended_request(self):
        request = "create a python project with venv and tests and make it nice"
        plan = plan_from_template(request)
        decision = score_template_candidate(request, plan, classify_request_complexity(request))
        self.assertIn(decision.route, {"ai", "no_match"})
        self.assertLess(decision.confidence, 0.8)

    def test_debug_route_contains_expected_fields(self):
        request = "change into the directory oop ss26 at least its named something like that - change the current directory"
        decision = score_template_candidate(request, plan_from_template(request), classify_request_complexity(request))
        text = format_route_debug(request, decision)
        self.assertIn("complexity:", text)
        self.assertIn("candidate:", text)
        self.assertIn("confidence:", text)
        self.assertIn("route:", text)
        self.assertIn("ignored tokens:", text)


if __name__ == "__main__":
    unittest.main()
