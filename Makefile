.PHONY: test test-fast test-ai compile check secret-check clean

test: compile
	python3 scripts/run_tests.py --cases tests/cases/testcases.json --html reports/testreport.html --json reports/results.json
	python3 -m unittest discover -s tests -p "test_*.py"

test-fast: test

test-ai:
	python3 -m cairos.cli config ai test || true

compile:
	python3 -m compileall -q cairos scripts

check: compile test secret-check

secret-check:
	@if grep -R "AQ\\." -n --exclude-dir=.git --exclude-dir=.venv --exclude=results.json --exclude=testreport.html .; then echo "Potential raw API key found"; exit 1; fi
	@if grep -R "GEMINI_API_KEY=.*[A-Za-z0-9_\\-]\\{20,\\}" -n --exclude-dir=.git --exclude-dir=.venv .; then echo "Potential raw Gemini key assignment found"; exit 1; fi

clean:
	rm -rf reports .pytest_cache **/__pycache__ cairos.egg-info build dist
