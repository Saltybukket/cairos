import subprocess
from .models import Plan
from .safety import check_commands


def execute_plan(plan: Plan, yes: bool = False) -> int:
    if not plan.commands:
        print("Nothing to execute.")
        return 1

    safety = check_commands(plan.commands)
    if safety.blocked:
        print(f"Blocked. Risk: {safety.risk}")
        for reason in safety.reasons:
            print(f"- {reason}")
        return 2

    print(f"Plan: {plan.summary}")
    print(f"Risk: {safety.risk}")
    for index, command in enumerate(plan.commands, 1):
        print(f"{index}. {command}")

    if not yes:
        answer = input("Execute? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 130

    for command in plan.commands:
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}: {command}")
            return result.returncode
    return 0
