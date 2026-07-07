import unittest

from cairos.router import classify_request_complexity, format_route_debug, score_template_candidate
from cairos.templates import plan_from_template


class RouterTests(unittest.TestCase):
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
