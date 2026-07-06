import unittest

from cairos.templates import _extract_named_value, plan_from_template


class TemplateParserTests(unittest.TestCase):
    def test_named_value_extraction(self):
        self.assertEqual(_extract_named_value('named new_cpp_project', 'any'), 'new_cpp_project')
        self.assertEqual(_extract_named_value('named "main_cpp.cpp"', 'any'), 'main_cpp.cpp')
        self.assertEqual(_extract_named_value('class called TestSubject', 'class'), 'TestSubject')
        self.assertEqual(_extract_named_value('file named main_cpp.cpp', 'file'), 'main_cpp.cpp')
        self.assertEqual(_extract_named_value('folder named new_cpp_project', 'folder'), 'new_cpp_project')

    def test_compound_cpp_request(self):
        plan = plan_from_template(
            'create a folder in this directory named new_cpp_project with one file named "main_cpp.cpp" '
            'which has a main function inside, headerguards with ifndef and a class called TestSubject'
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.source, 'template:cpp_compound')
        self.assertIn('new_cpp_project/main_cpp.cpp', plan.steps[1].path)
        self.assertIn('class TestSubject', plan.steps[1].content or '')
        self.assertIn('int main()', plan.steps[1].content or '')

    def test_complex_request_does_not_use_simple_file_template(self):
        plan = plan_from_template('create a project folder with a file that has a class')
        self.assertIsNone(plan)


if __name__ == '__main__':
    unittest.main()
