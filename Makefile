.PHONY: test test-fast test-ai compile check docs-check secret-check clean

test: compile
	python3 scripts/run_tests.py --cases tests/cases/testcases.json --html reports/testreport.html --json reports/results.json
	python3 -m unittest discover -s tests -p "test_*.py"

test-fast: test

test-ai:
	python3 -m cairos.cli config ai test || true

compile:
	python3 -m compileall -q cairos scripts

check: compile test docs-check secret-check

docs-check:
	@if grep -R "gemini-1.5-flash" -n --include="*.md" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=reports cairos scripts .; then echo "Stale Gemini model reference found"; exit 1; fi
	@if grep -R "<user>/<repo>\|github.com/<user>" -n --include="*.md" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=reports cairos scripts .; then echo "Placeholder GitHub URL found"; exit 1; fi
	@if grep -R "name = \"cairos\"" -n pyproject.toml; then echo "Stale package name found"; exit 1; fi

secret-check:
	@if grep -R "AQ\\." -n --exclude-dir=.git --exclude-dir=.venv --exclude-dir=reports --exclude=results.json --exclude=testreport.html .; then echo "Potential raw API key found"; exit 1; fi
	@if grep -R "GEMINI_API_KEY=.*[A-Za-z0-9_\\-]\\{30,\\}" -n --exclude-dir=.git --exclude-dir=.venv --exclude-dir=reports .; then echo "Potential raw Gemini key assignment found"; exit 1; fi

clean:
	rm -rf reports .pytest_cache .mypy_cache .ruff_cache cairos.egg-info cairos_shell.egg-info build dist
	find cairos scripts tests -type d -name __pycache__ -prune -exec rm -rf {} +
