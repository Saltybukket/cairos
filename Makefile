.PHONY: test test-fast test-ai compile check docs-check secret-check release-check clean

test: compile
	python3 scripts/run_tests.py --cases tests/cases/testcases.json --html reports/testreport.html --json reports/results.json
	python3 -m unittest discover -s tests -p "test_*.py"

test-fast: test

test-ai:
	python3 -m cairos.cli config ai test || true

compile:
	python3 -m compileall -q cairos scripts tests

check: compile test docs-check secret-check

release-check: check
	rm -rf dist build *.egg-info cairos_shell.egg-info
	python3 -m venv .release-venv
	.release-venv/bin/python -m pip install --upgrade pip build twine
	.release-venv/bin/python -m build
	.release-venv/bin/python -m twine check dist/*

docs-check:
	@if grep -R "gemini-1.5-flash" -n --include="*.md" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.release-venv --exclude-dir=reports --exclude-dir=build --exclude-dir=dist cairos scripts .; then echo "Stale Gemini model reference found"; exit 1; fi
	@if grep -R "<user>/<repo>\|github.com/<user>" -n --include="*.md" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.release-venv --exclude-dir=reports --exclude-dir=build --exclude-dir=dist cairos scripts .; then echo "Placeholder GitHub URL found"; exit 1; fi
	@if grep -R "name = \"cairos\"" -n pyproject.toml; then echo "Stale package name found"; exit 1; fi
	python3 scripts/docs_check.py

secret-check:
	@if grep -R "AQ\\." -n --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.release-venv --exclude-dir=reports --exclude-dir=build --exclude-dir=dist --exclude=results.json --exclude=testreport.html .; then echo "Potential raw API key found"; exit 1; fi
	@if grep -R "GEMINI_API_KEY=.*[A-Za-z0-9_\\-]\\{30,\\}" -n --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.release-venv --exclude-dir=reports --exclude-dir=build --exclude-dir=dist .; then echo "Potential raw Gemini key assignment found"; exit 1; fi

clean:
	rm -rf reports .pytest_cache .mypy_cache .ruff_cache .release-venv cairos.egg-info cairos_shell.egg-info build dist
	find cairos scripts tests -type d -name __pycache__ -prune -exec rm -rf {} +
