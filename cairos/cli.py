from __future__ import annotations

import argparse
import sys
from . import __version__
from .config import ai_status, config_json, config_path, set_config_value
from .context import context_json, context_summary
from .executor import execute_plan
from .explain import explain_command
from .formatter import format_plan
from .planner import make_plan
from .rules import init_local_rules, rules_json, set_rule
from .safety import check_command

RESERVED = {"plan", "expand", "run", "check", "explain", "context", "config", "rules", "doctor", "help"}

USAGE = """CAIROS — Context-Aware Intelligent Runtime Operating Shell

Usage:
  cairos <task in natural language>
  cairos plan <task>
  cairos expand <task>
  cairos run <task> [--yes]
  cairos explain <shell command>
  cairos check <shell command>
  cairos context [--json]
  cairos config show
  cairos config ai status
  cairos config ai set-provider <none|ollama|openai|custom-command>
  cairos config ai set-model <model>
  cairos config ai set-endpoint <url>
  cairos config set <key.path> <value>
  cairos rules init
  cairos rules show
  cairos rules set <key.path> <value>
  cairos doctor

Examples:
  cairos create python project testapp with venv git pytest
  cairos create cpp header file Player
  cairos finish current branch and prepare push to origin main
  cairos explain git reset --soft HEAD~1
"""


def _join(parts: list[str]) -> str:
    return " ".join(parts).strip()


def _print_help() -> int:
    print(USAGE)
    return 0


def _handle_plan(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    print(format_plan(make_plan(_join(args))))
    return 0


def _handle_expand(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    plan = make_plan(_join(args), allow_ai=False)
    if not plan.steps:
        print("# CAIROS: no deterministic expansion matched", file=sys.stderr)
        return 1
    print(plan.joined())
    return 0


def _handle_run(args: list[str]) -> int:
    yes = False
    filtered: list[str] = []
    for arg in args:
        if arg == "--yes":
            yes = True
        else:
            filtered.append(arg)
    if not filtered:
        print("Missing task.", file=sys.stderr)
        return 1
    return execute_plan(make_plan(_join(filtered)), yes=yes)


def _handle_check(args: list[str]) -> int:
    if not args:
        print("Missing shell command.", file=sys.stderr)
        return 1
    command = _join(args)
    result = check_command(command)
    print(f"Risk: {result.risk}")
    print(f"Blocked: {'yes' if result.blocked else 'no'}")
    print("Reasons:")
    for reason in result.reasons:
        print(f"- {reason}")
    return 2 if result.blocked else 0


def _handle_explain(args: list[str]) -> int:
    if not args:
        print("Missing shell command.", file=sys.stderr)
        return 1
    print(explain_command(_join(args)))
    return 0


def _handle_context(args: list[str]) -> int:
    if "--json" in args:
        print(context_json())
    else:
        print(context_summary())
    return 0


def _handle_config(args: list[str]) -> int:
    if not args or args[0] == "show":
        print(config_json())
        return 0

    if args[:2] == ["ai", "status"]:
        print(ai_status())
        return 0

    if args[:3] == ["ai", "set-provider"] and len(args) >= 4:
        path = set_config_value("ai.provider", args[3])
        print(f"Updated {path}: ai.provider={args[3]}")
        return 0

    if args[:3] == ["ai", "set-model"] and len(args) >= 4:
        path = set_config_value("ai.model", args[3])
        print(f"Updated {path}: ai.model={args[3]}")
        return 0

    if args[:3] == ["ai", "set-endpoint"] and len(args) >= 4:
        path = set_config_value("ai.endpoint", args[3])
        print(f"Updated {path}: ai.endpoint={args[3]}")
        return 0

    if args[:3] == ["ai", "set-api-key-env"] and len(args) >= 4:
        path = set_config_value("ai.api_key_env", args[3])
        print(f"Updated {path}: ai.api_key_env={args[3]}")
        return 0

    if args[:3] == ["ai", "set-custom-command"] and len(args) >= 4:
        command = _join(args[3:])
        path = set_config_value("ai.custom_command", command)
        print(f"Updated {path}: ai.custom_command={command}")
        return 0

    if args[0] == "set" and len(args) >= 3:
        path = set_config_value(args[1], _join(args[2:]))
        print(f"Updated {path}: {args[1]}={_join(args[2:])}")
        return 0

    print("Unknown config command.", file=sys.stderr)
    return 1


def _handle_rules(args: list[str]) -> int:
    if not args or args[0] == "show":
        print(rules_json())
        return 0
    if args[0] == "init":
        path = init_local_rules()
        print(f"Rules file ready: {path}")
        return 0
    if args[0] == "set" and len(args) >= 3:
        path = set_rule(args[1], _join(args[2:]))
        print(f"Updated {path}: {args[1]}={_join(args[2:])}")
        return 0
    print("Unknown rules command.", file=sys.stderr)
    return 1


def _handle_doctor() -> int:
    print("CAIROS Doctor")
    print(f"version: {__version__}")
    print(f"config path: {config_path()}")
    print(ai_status())
    print("Context:")
    print(context_summary())
    return 0


def _handle_free_task(args: list[str]) -> int:
    plan = make_plan(_join(args))
    if not plan.steps:
        print(format_plan(plan))
        return 1
    return execute_plan(plan, yes=False)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"-h", "--help", "help"}:
        return _print_help()

    if args[0] == "--version":
        print(__version__)
        return 0

    command = args[0]
    rest = args[1:]

    if command == "plan":
        return _handle_plan(rest)
    if command == "expand":
        return _handle_expand(rest)
    if command == "run":
        return _handle_run(rest)
    if command == "check":
        return _handle_check(rest)
    if command == "explain":
        return _handle_explain(rest)
    if command == "context":
        return _handle_context(rest)
    if command == "config":
        return _handle_config(rest)
    if command == "rules":
        return _handle_rules(rest)
    if command == "doctor":
        return _handle_doctor()

    return _handle_free_task(args)


if __name__ == "__main__":
    raise SystemExit(main())
