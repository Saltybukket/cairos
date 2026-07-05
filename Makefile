.PHONY: test report clean install editable

PYTHON ?= python3

install editable:
	$(PYTHON) -m pip install -e .

test report:
	$(PYTHON) scripts/run_tests.py --cases tests/cases/testcases.json --html reports/testreport.html --json reports/results.json

clean:
	rm -rf reports/*.html reports/*.json .pytest_cache __pycache__ cairos/__pycache__ scripts/__pycache__ *.egg-info build dist
