#!/usr/bin/env python3
import argparse
import difflib
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STYLE = """
body { font-family: Arial, sans-serif; color: #222; max-width: 110em; margin: auto; }
h1 { text-align: center; font-size: 3em; }
h2 { border-bottom: 0.1em solid #666; margin-top: 3em; }
table { border-collapse: collapse; }
th, td { padding: 0.45em 0.8em; vertical-align: top; }
tr:hover { background: #eee; }
.shortreport { margin: 2em auto; }
.shortreport th { border-bottom: 0.1em solid #222; }
.success { color: green; font-family: monospace; font-weight: bold; }
.fail { color: darkred; font-family: monospace; font-weight: bold; }
.inline-code, pre { background: #eee; font-family: monospace; font-size: 0.92em; }
pre { padding: 1em; white-space: pre-wrap; word-break: break-word; }
.diff { width: 100%; }
.diff table { width: 100%; background: #eee; margin-top: 1em; }
.diff td { width: 50%; font-family: monospace; white-space: pre-wrap; word-break: break-word; }
.diff-add { background-color: #9acd32b8; }
.diff-remove { background-color: #cd5c5cb0; }
.warning { background: #ff000033; color: darkred; padding: 0.5em; border-left: darkred 0.4em solid; }
.flex-container { display: flex; justify-content: center; }
.shortinfo th { text-align: right; border-right: 0.1em solid #222; }
"""


def normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n")


def diff_percent(expected: str, actual: str) -> int:
    if expected == actual:
        return 100
    matcher = difflib.SequenceMatcher(a=expected, b=actual)
    return int(round(matcher.ratio() * 100))


def command_to_str(cmd: list[str]) -> str:
    return " ".join(cmd)


def run_case(case: dict, index: int, timeout: int) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd()) + os.pathsep + env.get("PYTHONPATH", "")
    start = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            case["command"],
            cwd=Path.cwd(),
            env=env,
            text=True,
            capture_output=True,
            timeout=case.get("timeout", timeout),
        )
        stdout = normalize_newlines(proc.stdout)
        stderr = normalize_newlines(proc.stderr)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = normalize_newlines(exc.stdout or "")
        stderr = normalize_newlines(exc.stderr or "")
        exit_code = -999

    expected_stdout = case.get("expected_stdout")
    expected_stderr = case.get("expected_stderr", "")
    expected_exit = case.get("expected_exit", 0)
    expected_contains = case.get("expected_contains")

    if expected_contains is not None:
        output_ok = all(fragment in stdout for fragment in expected_contains)
        reference_for_diff = "\n".join(expected_contains) + "\n"
    else:
        output_ok = stdout == expected_stdout and stderr == expected_stderr
        reference_for_diff = (expected_stdout or "") + (expected_stderr or "")

    actual_combined = stdout + stderr
    exit_ok = exit_code == expected_exit
    passed = output_ok and exit_ok and not timed_out
    return {
        "index": index,
        "name": case["name"],
        "command": command_to_str(case["command"]),
        "passed": passed,
        "timeout": timed_out,
        "expected_exit": expected_exit,
        "actual_exit": exit_code,
        "expected_stdout": expected_stdout,
        "expected_stderr": expected_stderr,
        "expected_contains": expected_contains,
        "actual_stdout": stdout,
        "actual_stderr": stderr,
        "diff_percent": diff_percent(reference_for_diff, actual_combined),
        "duration_ms": int((time.time() - start) * 1000),
    }


def html_diff(expected: str, actual: str) -> str:
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)
    left = []
    right = []
    for line in difflib.ndiff(expected_lines, actual_lines):
        tag = line[:2]
        text = html.escape(line[2:])
        if tag == "  ":
            left.append(text)
            right.append(text)
        elif tag == "- ":
            left.append(f'<span class="diff-remove">{text}</span>')
        elif tag == "+ ":
            right.append(f'<span class="diff-add">{text}</span>')
    return f"""
<table>
<tr><th>Reference Output</th><th>Your Output</th></tr>
<tr><td>{''.join(left) or '&lt;empty&gt;'}</td><td>{''.join(right) or '&lt;empty&gt;'}</td></tr>
</table>
"""


def render_report(results: list[dict]) -> str:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    rows = []
    details = []
    for r in results:
        mark = '<span class="success">✔</span>' if r["passed"] else '<span class="fail">✘</span>'
        rows.append(f"""
<tr>
<td><a href="#tc-{r['index']}">#{r['index']:02d}: {html.escape(r['name'])}</a></td>
<td>{mark}</td>
<td>{r['diff_percent']}%</td>
<td>{'correct' if r['actual_exit'] == r['expected_exit'] else f"expected {r['expected_exit']}, got {r['actual_exit']}"}</td>
<td>{'yes' if r['timeout'] else 'no'}</td>
<td>{r['duration_ms']} ms</td>
</tr>
""")
        if r["expected_contains"] is not None:
            expected = "Expected stdout to contain:\n" + "\n".join(r["expected_contains"]) + "\n"
        else:
            expected = (r["expected_stdout"] or "") + (r["expected_stderr"] or "")
        actual = r["actual_stdout"] + r["actual_stderr"]
        details.append(f"""
<div class="long_report">
<h2>#{r['index']:02d}: <a id="tc-{r['index']}"></a>{html.escape(r['name'])} <a style="float:right;font-size:0.7em" href="#summary">back to summary</a></h2>
<div class="shortinfo"><table>
<tr><th>Passed</th><td>{mark}</td></tr>
<tr><th>Commandline</th><td><span class="inline-code">{html.escape(r['command'])}</span></td></tr>
<tr><th>Exit Code</th><td>expected: <span class="inline-code">{r['expected_exit']}</span>, got: <span class="inline-code">{r['actual_exit']}</span></td></tr>
<tr><th>Output-Diff</th><td>{r['diff_percent']}%</td></tr>
<tr><th>Timeout</th><td>{'yes' if r['timeout'] else 'no'}</td></tr>
<tr><th>Duration</th><td>{r['duration_ms']} ms</td></tr>
</table></div>
<div class="diff">{html_diff(expected, actual)}</div>
</div>
""")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>CAIROS Testreport</title><style>{STYLE}</style></head>
<body>
<h1>CAIROS Testreport</h1>
<h2><a id="summary"></a>Summary</h2>
<div class="flex-container"><div class="shortinfo"><table>
<tr><th>Public Testcases</th><td>{passed} / {total} ({round((passed/total)*100 if total else 0)}%)</td></tr>
<tr><th>All Testcases</th><td>{passed} / {total} ({round((passed/total)*100 if total else 0)}%)</td></tr>
</table></div></div>
<table class="shortreport">
<tr><th>Name</th><th>Passed</th><th>Diff</th><th>Exit Code</th><th>Timeout</th><th>Duration</th></tr>
{''.join(rows)}
</table>
<h2>Testcases</h2>
{''.join(details)}
</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--timeout", type=int, default=5)
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    results = [run_case(case, i + 1, args.timeout) for i, case in enumerate(cases)]

    Path(args.html).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.html).write_text(render_report(results), encoding="utf-8")
    Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"CAIROS tests: {passed}/{total} passed")
    print(f"HTML report: {args.html}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
