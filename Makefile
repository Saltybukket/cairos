.PHONY: test compile clean

test: compile
	python3 scripts/run_tests.py --cases tests/cases/testcases.json --html reports/testreport.html --json reports/results.json

compile:
	python3 -m compileall -q cairos scripts

clean:
	rm -rf reports .pytest_cache **/__pycache__ cairos.egg-info build dist
