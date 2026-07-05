import argparse
import sys
from . import __version__
from .planner import make_plan
from .formatter import format_plan
from .safety import check_command
from .executor import execute_plan
from .context import context_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairos", description="Context-Aware Intelligent Runtime Operating Shell")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    sub = parser.add_subparsers(dest="command")

    p_plan = sub.add_parser("plan", help="create a command plan")
    p_plan.add_argument("request", nargs="+", help="natural-language request")

    p_expand = sub.add_parser("expand", help="print only the shell command expansion")
    p_expand.add_argument("request", nargs="+", help="natural-language request")

    p_check = sub.add_parser("check", help="check command safety")
    p_check.add_argument("shell_command", nargs="+", help="shell command to check")

    p_explain = sub.add_parser("explain", help="explain a command safety level")
    p_explain.add_argument("shell_command", nargs="+", help="shell command to explain")

    p_run = sub.add_parser("run", help="execute a planned request")
    p_run.add_argument("request", nargs="+", help="natural-language request")
    p_run.add_argument("--yes", action="store_true", help="execute without interactive confirmation")

    sub.add_parser("context", help="print compact shell context as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.command == "plan":
        request = " ".join(args.request)
        print(format_plan(make_plan(request)))
        return 0

    if args.command == "expand":
        request = " ".join(args.request)
        plan = make_plan(request)
        if not plan.commands:
            print("# CAIROS: no matching template", file=sys.stderr)
            return 1
        print(plan.joined())
        return 0

    if args.command == "check":
        command = " ".join(args.shell_command)
        result = check_command(command)
        print(f"Risk: {result.risk}")
        print(f"Blocked: {'yes' if result.blocked else 'no'}")
        print("Reasons:")
        for reason in result.reasons:
            print(f"- {reason}")
        return 2 if result.blocked else 0

    if args.command == "explain":
        command = " ".join(args.shell_command)
        result = check_command(command)
        print(f"Command: {command}")
        print(f"Risk: {result.risk}")
        for reason in result.reasons:
            print(f"- {reason}")
        return 0

    if args.command == "run":
        request = " ".join(args.request)
        return execute_plan(make_plan(request), yes=args.yes)

    if args.command == "context":
        print(context_json())
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
