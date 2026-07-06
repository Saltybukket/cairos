"""Plan execution and verification for CAIROS.

The executor is the only module that should modify the filesystem or run shell
commands. It always re-runs safety checks before executing a plan.
"""

from __future__ import annotations

import subprocess
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

    for step in plan.steps:
        exit_code = _execute_step(step)
        if exit_code != 0:
            print(f"Step failed with exit code {exit_code}: {step.display()}")
            return exit_code

    if plan.verification:
        print("Verification:")
        failed = False
        for item in plan.verification:
            ok, label = _verify(item)
            print(f"{'✔' if ok else '✘'} {label}")
            failed = failed or not ok
        if failed:
            return 3

    print("Done.")
    return 0
