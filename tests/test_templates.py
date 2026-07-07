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

    def test_cd_guidance_windows_cmd(self):
        plan = plan_from_template('go into the directory TU-Graz. mind that you are in windows cmd')
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.source, 'template:cd-guidance')
        self.assertIn('cairos find-dir "TU-Graz"', plan.steps[0].command or '')
        self.assertNotIn('find . -maxdepth', plan.steps[0].command or '')
        self.assertIn('parent shell', '\n'.join(plan.notes))

    def test_cd_guidance_powershell_and_posix(self):
        ps = plan_from_template('go into the directory my folder mind that you are in powershell')
        self.assertIsNotNone(ps)
        assert ps is not None
        self.assertIn('cairos find-dir "my folder"', ps.steps[0].command or '')
        bash = plan_from_template('go into the directory TU-Graz mind that you are in bash')
        self.assertIsNotNone(bash)
        assert bash is not None
        self.assertIn('cairos find-dir "TU-Graz"', bash.steps[0].command or '')

    def test_fuzzy_directory_fillers_are_not_targets(self):
        examples = [
            'go into the directory oop ss26 at least its named something like that',
            'go into the directory oop ss26 or something',
            'cd into oop ss26 maybe',
            'find directory TU Graz something like that',
            'go into directory Analysis 2 glaube ich',
        ]
        for request in examples:
            with self.subTest(request=request):
                plan = plan_from_template(request + ' mind that you are in bash')
                self.assertIsNotNone(plan)
                assert plan is not None
                command = plan.steps[0].command or ''
                self.assertNotIn('*something*', command)
                self.assertIn('cairos find-dir', command)
        plan = plan_from_template('go into the directory oop ss26 at least its named something like that mind that you are in bash')
        assert plan is not None
        self.assertIn('oop', plan.steps[0].command or '')
        self.assertIn('ss26', plan.steps[0].command or '')

    def test_fuzzy_directory_shell_specific_commands(self):
        cmd = plan_from_template('go into the directory oop ss26 or something mind that you are in windows cmd')
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertIn('cairos find-dir "oop ss26"', cmd.steps[0].command or '')
        self.assertNotIn('find . -maxdepth', cmd.steps[0].command or '')
        ps = plan_from_template('go into the directory oop ss26 or something mind that you are in powershell')
        self.assertIsNotNone(ps)
        assert ps is not None
        self.assertIn('cairos find-dir "oop ss26"', ps.steps[0].command or '')


if __name__ == '__main__':
    unittest.main()
