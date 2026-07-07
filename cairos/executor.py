"""Plan execution and verification for CAIROS.

The executor is the only module that should modify the filesystem or run shell
commands. It always re-runs safety checks before executing a plan.
"""

from __future__ import annotations

import subprocess
import sys
import shlex
from pathlib import Path
from .models import CommandStep, Plan, VerificationStep
from .safety import check_steps


def _execute_step(step: CommandStep) -> int:
    if step.kind == "command":
        if not step.command:
            print("Empty command step.")
            return 1
        result = subprocess.run(step.command, shell=True)
        return result.returncode

    if step.kind == "mkdir":
        if not step.path:
            print("mkdir step has no path.")
            return 1
        Path(step.path).mkdir(parents=True, exist_ok=True)
        return 0

    if step.kind in {"write_file", "append_file"}:
        if not step.path:
            print(f"{step.kind} step has no path.")
            return 1
        path = Path(step.path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if step.kind == "append_file" else "w"
        with path.open(mode, encoding="utf-8") as handle:
            handle.write(step.content or "")
        return 0

    print(f"Unsupported step kind: {step.kind}")
    return 1


def _execute_navigation_step(step: CommandStep, plan: Plan) -> tuple[int, list[str]]:
    if not step.command:
        print("Empty command step.")
        return 1, []
    exit_code = 0
    stderr = ""
    if step.command.startswith("cairos find-dir "):
        output_lines = _run_find_dir_step(step.command)
        if not output_lines:
            exit_code = 1
    else:
        proc = subprocess.run(step.command, shell=True, text=True, capture_output=True)
        output_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        stderr = proc.stderr.strip()
        exit_code = proc.returncode
    if output_lines:
        print("Matches:")
        for index, line in enumerate(output_lines, 1):
            print(f"{index}. {line}" if len(output_lines) > 1 else line)
    else:
        print("No matching directories found.")
    if stderr:
        print(stderr)
    if len(output_lines) == 1:
        for note in plan.notes:
            if "<matched-path>" in note:
                print("Copy-paste command:")
                print(note.split("run:", 1)[-1].strip().replace("<matched-path>", output_lines[0]))
                break
    elif len(output_lines) > 1:
        print("Choose one matching path and use the cd command pattern below.")
    return exit_code, output_lines


def _run_find_dir_step(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    if len(parts) < 3 or parts[:2] != ["cairos", "find-dir"]:
        return []
    query = " ".join(parts[2:]).strip()
    if not query:
        return []
    from .cli import _find_dirs

    return [str(path) for path in _find_dirs(query, start=Path.cwd())]


def _verify(item: VerificationStep) -> tuple[bool, str]:
    if item.kind == "file_exists":
        return Path(item.target).is_file(), f"file exists: {item.target}"
    if item.kind == "dir_exists":
        return Path(item.target).is_dir(), f"directory exists: {item.target}"
    if item.kind == "command_succeeds":
        proc = subprocess.run(item.target, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0, f"command succeeds: {item.target}"
    if item.kind == "command_output_equals":
        proc = subprocess.run(item.target, shell=True, text=True, capture_output=True)
        actual = proc.stdout.strip()
        return proc.returncode == 0 and actual == item.expected, f"command output equals {item.expected!r}: {item.target}"
    return False, f"unknown verification: {item.kind} {item.target}"


def execute_plan(plan: Plan, yes: bool = False) -> int:
    if not plan.steps:
        print("Nothing to execute.")
        return 1

    safety = check_steps(plan.steps)
    if safety.blocked or safety.risk == "critical":
        print(f"Blocked. Risk: {safety.risk}")
        for reason in safety.reasons:
            print(f"- {reason}")
        return 2

    if plan.notices:
        for notice in plan.notices:
            print(notice)
        print("")

    print(f"Plan: {plan.summary}")
    print(f"Source: {plan.source}")
    print(f"Risk: {safety.risk}")
    for index, step in enumerate(plan.steps, 1):
        print(f"{index}. {step.display()}")
        print(f"   {step.description}")

    phrase = plan.confirmation_phrase or "yes"
    if plan.requires_confirmation and not yes:
        try:
            answer = input(f'Type "{phrase}" to execute: ').strip()
        except EOFError:
            print("Aborted: confirmation input was not available.")
            return 130
        if answer != phrase:
            print("Aborted.")
            return 130

    navigation_exit_code: int | None = None
    for step in plan.steps:
        sys.stdout.flush()
        if plan.source == "template:cd-guidance" and step.kind == "command" and (step.command or "").startswith("cairos find-dir "):
            exit_code, _ = _execute_navigation_step(step, plan)
            navigation_exit_code = exit_code
        else:
            exit_code = _execute_step(step)
        if exit_code != 0:
            if plan.source != "template:cd-guidance":
                print(f"Step failed with exit code {exit_code}: {step.display()}")
                return exit_code
            navigation_exit_code = exit_code
            break

    if plan.verification:
        print("Verification:")
        failed = False
        for item in plan.verification:
            ok, label = _verify(item)
            print(f"{'✔' if ok else '✘'} {label}")
            failed = failed or not ok
        if failed:
            return 3

    if plan.source == "template:cd-guidance" and plan.notes:
        print("Next:")
        for note in plan.notes:
            print(f"- {note}")
        if navigation_exit_code not in {None, 0}:
            return navigation_exit_code

    print("Done.")
    return 0
