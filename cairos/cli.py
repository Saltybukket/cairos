"""Command-line interface for CAIROS.

The CLI supports both explicit subcommands and the main natural-language style:

    cairos create python project demo with venv git

Reserved commands like ``explain`` and ``config`` keep predictable behavior,
while everything else is treated as a task and passed to the planner.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from . import __version__
from .ai import ai_self_test, list_models
from .config import (
    ai_status,
    activate_ai_profile,
    active_ai_profile_name,
    ai_profiles,
    config_dir,
    config_json,
    config_path,
    configure_gemini,
    configure_custom_command,
    configure_ollama,
    configure_openai,
    delete_ai_profile,
    disable_ai,
    env_var_setup_hint,
    load_config,
    rename_ai_profile,
    save_current_ai_profile,
    set_config_value,
    shell_guess,
    state_dir,
)
from .context import context_json, context_summary
from .executor import execute_plan
from .explain import explain_command
from .formatter import format_plan
from .history import append_history, clear_history, format_history, history_path
from .planner import make_plan
from .preview import diff_plan, preview_plan
from .rules import init_global_rules, init_local_rules, local_rules_path, rules_json, set_rule
from .safety import check_command
from .text import looks_like_shell_command

RESERVED = {"plan", "expand", "run", "check", "explain", "context", "config", "rules", "doctor", "history", "preview", "diff", "help"}

USAGE = """CAIROS — Context-Aware Intelligent Runtime Operating Shell

Usage:
  cairos <task in natural language>
  cairos plan <task>
  cairos expand <task>
  cairos run <task> [--yes]
  cairos --dry-run <task>
  cairos preview <task>
  cairos diff <task>
  cairos explain <shell command>
  cairos check <shell command | natural language task>
  cairos context [--json]
  cairos find-dir <name>
  cairos config show
  cairos config path
  cairos config ai status
  cairos config ai test
  cairos config ai list-models
  cairos config ai use-ollama [model] [--endpoint URL]
  cairos config ai use-openai [model] [--api-key-env ENV] [--endpoint URL]
  cairos config ai use-gemini [model] [--api-key-env ENV]
  cairos config ai use-custom <command>
  cairos config ai disable
  cairos ai <config-ai command>
  cairos config set <key.path> <value>
  cairos rules init [--global]
  cairos rules show
  cairos rules set <key.path> <value> [--global]
  cairos doctor
  cairos install-info
  cairos quicksetup
  cairos init [--global]
  cairos setup
  cairos templates [python|cpp|git|ai|system|wsl|windows|node|rust|files|cleanup]
  cairos shell install zsh|powershell
  cairos completion zsh|powershell
  cairos history [last|clear]

Examples:
  cairos check if repo is ready to commit
  cairos plan create python project demo with venv git pytest
  cairos run create folder docs
  cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
  cairos macke python projekt testapp mit venv git pytest
  cairos create cpp header file Player
"""


def _join(parts: list[str]) -> str:
    """Join CLI argument tokens into one request string."""
    return " ".join(parts).strip()


def _extract_flag_value(args: list[str], flag: str, default: str) -> str:
    """Extract a simple ``--flag value`` pair from args."""
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return default


def _without_flags(args: list[str], flags: set[str]) -> list[str]:
    """Return args with simple ``--flag value`` pairs removed."""
    out: list[str] = []
    skip_next = False
    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in flags:
            skip_next = index + 1 < len(args)
            continue
        out.append(arg)
    return out


def _print_help() -> int:
    print(USAGE)
    return 0


def _print_try_help() -> int:
    print("CAIROS — Context-Aware Intelligent Runtime Operating Shell")
    print("")
    print("Try:")
    print("  cairos quicksetup")
    print("  cairos doctor")
    print("  cairos check if repo is ready to commit")
    print("  cairos plan create python project demo with venv git pytest")
    print("")
    print("Run:")
    print("  cairos --help")
    return 0


def _handle_plan(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    if args[0] == "--debug-match":
        from .templates import debug_match_report
        print(debug_match_report(_join(args[1:])))
        return 0
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
    yes = "--yes" in args
    filtered = [arg for arg in args if arg != "--yes"]
    if not filtered:
        print("Missing task.", file=sys.stderr)
        return 1
    request = _join(filtered)
    plan = make_plan(request)
    exit_code = execute_plan(plan, yes=yes)
    append_history(request, plan.source, plan.risk, exit_code == 0, exit_code)
    return exit_code


def _handle_dry_run(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    print(format_plan(make_plan(_join(args))))
    print("Dry-run: no steps executed.")
    return 0


def _handle_preview(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    print(preview_plan(make_plan(_join(args))))
    return 0


def _handle_diff(args: list[str]) -> int:
    if not args:
        print("Missing task.", file=sys.stderr)
        return 1
    print(diff_plan(make_plan(_join(args))))
    return 0


def _handle_check(args: list[str]) -> int:
    if not args:
        print("Missing shell command.", file=sys.stderr)
        return 1
    command = _join(args)
    if not looks_like_shell_command(command):
        print(format_plan(make_plan(f"check {command}")))
        return 0
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
    print(context_json() if "--json" in args else context_summary())
    return 0


def _ai_help_text() -> str:
    return """CAIROS AI configuration

Status:
  cairos config ai status
  cairos config ai test

Profiles:
  cairos config ai profiles
  cairos config ai switch
  cairos config ai use-profile <name>
  cairos config ai save-profile <name>
  cairos config ai delete-profile <name>

Providers:
  cairos config ai list-providers
  cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash
  cairos config ai use-openai gpt-4.1-mini --profile openai-mini
  cairos config ai use-ollama llama3.1 --profile ollama-local
  cairos config ai use-custom <command> --profile custom-local
  cairos config ai disable

Models:
  cairos config ai list-models

Never store raw API keys in CAIROS config. Store only environment variable names."""


def _print_env_next(env_name: str) -> None:
    print("Next:")
    print(env_var_setup_hint(env_name))
    print("Then test: cairos config ai test")


def _print_provider_list() -> None:
    print("Supported AI providers:")
    print("- none")
    print("- ollama")
    print("- gemini")
    print("- openai")
    print("- custom-command")
    print("")
    print("Setup examples:")
    print("  cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash")
    print("  cairos config ai use-openai gpt-4.1-mini --profile openai-mini")
    print("  cairos config ai use-ollama llama3.1 --profile ollama-local")


def _profile_key_status(profile: dict[str, object]) -> str:
    provider = str(profile.get("provider", "none"))
    env_name = str(profile.get("api_key_env", "") or "")
    if provider in {"ollama", "none", "custom-command"} or not env_name:
        return "local" if provider == "ollama" else "none"
    return "available" if os.environ.get(env_name) else "missing"


def _format_profile_summary(name: str, profile: dict[str, object], active: str) -> list[str]:
    mark = "*" if name == active else " "
    env_name = str(profile.get("api_key_env", "") or "none")
    return [
        f"{mark} {name}",
        f"  provider: {profile.get('provider', 'none')}",
        f"  model: {profile.get('model', '') or '<not set>'}",
        f"  endpoint: {profile.get('endpoint', '') or '<not set>'}",
        f"  key env: {env_name}",
        f"  key available: {_profile_key_status(profile)}",
    ]


def _profiles_text() -> str:
    profiles = ai_profiles()
    active = active_ai_profile_name()
    if not profiles:
        return "AI Profiles\n\nNo saved AI profiles yet.\nTry: cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash"
    lines = ["AI Profiles", ""]
    for name in sorted(profiles):
        lines.extend(_format_profile_summary(name, profiles[name], active))
        lines.append("")
    return "\n".join(lines).rstrip()


def _print_unknown_ai_command(command: str) -> int:
    print(f"Unknown AI config command: {command}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Try:", file=sys.stderr)
    print("  cairos config ai --help", file=sys.stderr)
    print("  cairos config ai status", file=sys.stderr)
    print("  cairos config ai profiles", file=sys.stderr)
    print("  cairos config ai list-providers", file=sys.stderr)
    if "cairos" in command:
        print("", file=sys.stderr)
        print("It looks like two commands may have been pasted together.", file=sys.stderr)
        print("Run them separately, for example:", file=sys.stderr)
        print("  cairos config ai list-providers", file=sys.stderr)
        print("  cairos config ai status", file=sys.stderr)
    return 1


def _iter_find_dir_roots() -> list[Path]:
    home = Path.home()
    roots = [Path.cwd(), home, home / "projects", home / "Desktop", home / "Documents", home / "Downloads"]
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        try:
            key = str(root.resolve())
        except OSError:
            key = str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _find_dir(name: str, max_depth: int = 3, max_dirs_scanned: int = 300) -> Path | None:
    target = name.lower()
    scanned = 0
    ignored = {"appdata", ".git", ".venv", "venv", "env", "node_modules", ".local", "library", "onedrive"}

    def walk(root: Path, depth: int) -> Path | None:
        nonlocal scanned
        if scanned >= max_dirs_scanned or depth > max_depth:
            return None
        try:
            entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
        except (PermissionError, OSError):
            return None
        scanned += 1
        for entry in entries:
            try:
                if not entry.is_dir() or entry.is_symlink() or entry.name.lower() in ignored:
                    continue
                if entry.name.lower() == target:
                    return entry
                found = walk(entry, depth + 1)
                if found:
                    return found
            except (PermissionError, OSError):
                continue
        return None

    for root in _iter_find_dir_roots():
        if not root.exists() or not root.is_dir():
            continue
        if root.name.lower() == target:
            return root
        found = walk(root, 0)
        if found:
            return found
    return None


def _handle_find_dir(args: list[str]) -> int:
    if not args:
        print("Missing directory name.", file=sys.stderr)
        return 1
    found = _find_dir(_join(args))
    if not found:
        print("Directory not found within bounded search locations.", file=sys.stderr)
        return 1
    print(found)
    return 0


def _handle_config_ai(args: list[str]) -> int:
    """Handle ``cairos config ai ...`` commands."""
    if args and args[0] in {"-h", "--help", "help"}:
        print(_ai_help_text())
        return 0

    if not args or args[0] == "status":
        print(ai_status())
        return 0

    if args[0] == "test":
        print(ai_self_test())
        return 0

    if args[0] == "list-providers":
        _print_provider_list()
        return 0

    if args[0] in {"profiles", "list-profiles", "list"}:
        print(_profiles_text())
        return 0

    if args[0] in {"use-profile", "use"} and len(args) >= 2:
        name = args[1]
        try:
            activate_ai_profile(name)
        except KeyError:
            print(f"Unknown AI profile: {name}", file=sys.stderr)
            print("Run: cairos config ai profiles", file=sys.stderr)
            return 1
        ai = load_config()["ai"]
        print(f"Activated AI profile: {name}")
        print(f"provider={ai.get('provider')} model={ai.get('model') or '<not set>'} api_key_env={ai.get('api_key_env') or 'none'}")
        print("Next: cairos config ai test")
        return 0

    if args[0] == "show-profile" and len(args) >= 2:
        name = args[1]
        profiles = ai_profiles()
        if name not in profiles:
            print(f"Unknown AI profile: {name}", file=sys.stderr)
            return 1
        print("\n".join(_format_profile_summary(name, profiles[name], active_ai_profile_name())))
        return 0

    if args[0] == "save-profile" and len(args) >= 2:
        path = save_current_ai_profile(args[1])
        print(f"Saved current AI config as profile: {args[1]}")
        print(f"Updated {path}")
        return 0

    if args[0] == "delete-profile" and len(args) >= 2:
        force = "--force" in args
        try:
            path = delete_ai_profile(args[1], force=force)
        except ValueError:
            print("Cannot delete active profile. Switch to another profile first.", file=sys.stderr)
            return 1
        except KeyError:
            print(f"Unknown AI profile: {args[1]}", file=sys.stderr)
            return 1
        print(f"Deleted AI profile: {args[1]}")
        print(f"Updated {path}")
        return 0

    if args[0] == "rename-profile" and len(args) >= 3:
        try:
            path = rename_ai_profile(args[1], args[2])
        except KeyError:
            print(f"Unknown AI profile: {args[1]}", file=sys.stderr)
            return 1
        print(f"Renamed AI profile: {args[1]} -> {args[2]}")
        print(f"Updated {path}")
        return 0

    if args[0] in {"switch", "select"}:
        profiles = ai_profiles()
        if not profiles:
            print(_profiles_text())
            return 1
        names = sorted(profiles)
        print("Choose AI profile:")
        print("")
        for index, name in enumerate(names, 1):
            profile = profiles[name]
            print(f"[{index}] {name:<18} {profile.get('provider', 'none'):<8} {str(profile.get('model', '') or '<not set>'):<20} key: {_profile_key_status(profile)}")
        print("")
        if not sys.stdin.isatty():
            print("Non-interactive shell. Use:")
            print("  cairos config ai use-profile <name>")
            return 0
        answer = input("Enter number: ").strip()
        try:
            choice = int(answer)
            selected = names[choice - 1]
        except (ValueError, IndexError):
            print("Invalid selection.", file=sys.stderr)
            return 1
        return _handle_config_ai(["use-profile", selected])

    if args[0] == "list-models":
        print(list_models())
        return 0

    if args[0] in {"use-ollama", "set-local", "local", "ollama"}:
        model_args = _without_flags(args[1:], {"--endpoint", "--profile"})
        model = model_args[0] if model_args else "llama3.1"
        endpoint = _extract_flag_value(args, "--endpoint", "http://localhost:11434")
        profile = _extract_flag_value(args, "--profile", "")
        path = configure_ollama(model=model, endpoint=endpoint, profile=profile or None)
        print(f"Configured local Ollama AI in {path}")
        print(f"provider=ollama model={model} endpoint={endpoint}")
        print(f"active_profile={active_ai_profile_name() or '<none>'}")
        print(f"Next: ollama pull {model} && ollama serve")
        return 0

    if args[0] in {"use-openai", "openai", "api"}:
        model_args = _without_flags(args[1:], {"--api-key-env", "--endpoint", "--profile"})
        model = model_args[0] if model_args else "gpt-4.1-mini"
        api_key_env = _extract_flag_value(args, "--api-key-env", "OPENAI_API_KEY")
        endpoint = _extract_flag_value(args, "--endpoint", "https://api.openai.com/v1")
        profile = _extract_flag_value(args, "--profile", "")
        path = configure_openai(model=model, api_key_env=api_key_env, endpoint=endpoint, profile=profile or None)
        print(f"Configured OpenAI-compatible AI in {path}")
        print(f"provider=openai model={model} endpoint={endpoint} api_key_env={api_key_env}")
        print(f"active_profile={active_ai_profile_name() or '<none>'}")
        _print_env_next(api_key_env)
        return 0

    if args[0] in {"use-gemini", "gemini"}:
        model_args = _without_flags(args[1:], {"--api-key-env", "--profile"})
        model = model_args[0] if model_args else "gemini-2.5-flash"
        api_key_env = _extract_flag_value(args, "--api-key-env", "GEMINI_API_KEY")
        profile = _extract_flag_value(args, "--profile", "")
        path = configure_gemini(model=model, api_key_env=api_key_env, profile=profile or None)
        print(f"Configured Gemini AI in {path}")
        print(f"provider=gemini model={model} api_key_env={api_key_env}")
        print(f"active_profile={active_ai_profile_name() or '<none>'}")
        _print_env_next(api_key_env)
        return 0

    if args[0] == "set-gemini-key-env" and len(args) >= 2:
        path = set_config_value("ai.api_key_env", args[1])
        print(f"Updated {path}: ai.api_key_env={args[1]}")
        return 0

    if args[0] == "set-ollama-endpoint" and len(args) >= 2:
        path = set_config_value("ai.endpoint", args[1])
        print(f"Updated {path}: ai.endpoint={args[1]}")
        return 0

    if args[0] == "set-openai-endpoint" and len(args) >= 2:
        path = set_config_value("ai.endpoint", args[1])
        print(f"Updated {path}: ai.endpoint={args[1]}")
        return 0

    if args[0] == "set-openai-key-env" and len(args) >= 2:
        path = set_config_value("ai.api_key_env", args[1])
        print(f"Updated {path}: ai.api_key_env={args[1]}")
        return 0

    if args[0] in {"use-custom", "custom-command"} and len(args) >= 2:
        command_args = _without_flags(args[1:], {"--profile"})
        command = _join(command_args)
        profile = _extract_flag_value(args, "--profile", "")
        path = configure_custom_command(command, profile=profile or None)
        print(f"Configured custom AI command in {path}")
        print(f"custom_command={command}")
        print(f"active_profile={active_ai_profile_name() or '<none>'}")
        return 0

    if args[0] in {"disable", "off", "none"}:
        path = disable_ai()
        print(f"Disabled AI fallback in {path}")
        return 0

    # Backwards-compatible setters.
    if args[:2] == ["set-provider", "ollama"]:
        path = configure_ollama()
        print(f"Updated {path}: ai.provider=ollama")
        return 0
    if args[0] == "set-provider" and len(args) >= 2:
        path = set_config_value("ai.provider", args[1])
        print(f"Updated {path}: ai.provider={args[1]}")
        return 0
    if args[0] == "set-model" and len(args) >= 2:
        path = set_config_value("ai.model", args[1])
        print(f"Updated {path}: ai.model={args[1]}")
        return 0
    if args[0] == "set-endpoint" and len(args) >= 2:
        path = set_config_value("ai.endpoint", args[1])
        print(f"Updated {path}: ai.endpoint={args[1]}")
        return 0
    if args[0] == "set-api-key-env" and len(args) >= 2:
        path = set_config_value("ai.api_key_env", args[1])
        print(f"Updated {path}: ai.api_key_env={args[1]}")
        return 0

    return _print_unknown_ai_command(args[0])


def _handle_config(args: list[str]) -> int:
    if not args or args[0] == "show":
        print(config_json())
        return 0
    if args[0] == "path":
        print(config_path())
        return 0
    if args[0] == "ai":
        return _handle_config_ai(args[1:])
    if args[0] == "set" and len(args) >= 3:
        path = set_config_value(args[1], _join(args[2:]))
        print(f"Updated {path}: {args[1]}={_join(args[2:])}")
        return 0
    print("Unknown config command.", file=sys.stderr)
    return 1


def _handle_rules(args: list[str]) -> int:
    global_mode = "--global" in args
    filtered = [arg for arg in args if arg != "--global"]
    if not filtered or filtered[0] == "show":
        print(rules_json())
        return 0
    if filtered[0] == "init":
        path = init_global_rules() if global_mode else init_local_rules()
        print(f"Rules file ready: {path}")
        return 0
    if filtered[0] == "set" and len(filtered) >= 3:
        path = set_rule(filtered[1], _join(filtered[2:]), local=not global_mode)
        print(f"Updated {path}: {filtered[1]}={_join(filtered[2:])}")
        return 0
    print("Unknown rules command.", file=sys.stderr)
    return 1


def _handle_doctor() -> int:
    provider = load_config()["ai"].get("provider", "none")
    print("CAIROS Doctor")
    print(f"version: {__version__}")
    print(f"platform: {platform.system() or 'unknown'}")
    print(f"shell guess: {_shell_guess()}")
    print(f"python: {sys.version.split()[0]}")
    print(f"executable: {sys.executable}")
    print(f"config path: {config_path()}")
    print(f"history path: {history_path()}")
    print(f"command path: {shutil.which('cairos') or '<not found on PATH>'}")
    print(ai_status())
    print("AI hints:")
    if provider == "gemini":
        print("- Run `cairos config ai test` to verify the Gemini backend.")
        print("- Run `cairos config ai list-models` to inspect Gemini model availability.")
        print("- Run `cairos config ai profiles` to see saved profiles.")
    elif provider in {"openai", "openai-compatible"}:
        print("- Run `cairos config ai test` to verify the OpenAI-compatible backend.")
        print("- Run `cairos config ai profiles` to see saved profiles.")
    elif provider == "ollama":
        print("- Make sure Ollama is running: ollama serve")
        print("- Run `cairos config ai test`.")
        print("- Run `cairos config ai profiles` to see saved profiles.")
    elif provider == "none":
        print("- Configure AI with `cairos config ai list-providers`, or keep using offline templates.")
    else:
        print("- Run `cairos config ai test` to verify the configured backend.")
        print("- Run `cairos config ai profiles` to see saved profiles.")
    print("Context:")
    print(context_summary())
    git = check_command("git --version")
    print(f"git safety check: {git.risk}")
    return 0


def _user_bin_path() -> Path:
    """Return the common user-level script directory."""
    if platform.system() == "Windows":
        scripts = Path.home() / "AppData" / "Roaming" / "Python" / "Scripts"
        return Path(os.environ.get("PIPX_BIN_DIR", str(scripts)))
    return Path.home() / ".local" / "bin"


def _path_contains(path: Path) -> bool:
    """Return True when ``path`` appears in PATH."""
    target = str(path)
    return any(part.rstrip("/") == target for part in os.environ.get("PATH", "").split(os.pathsep) if part)


def _install_mode() -> str:
    """Best-effort description of how CAIROS is running."""
    exe = str(Path(sys.executable))
    module_path = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    if "pipx" in exe:
        return "pipx"
    if cwd == module_path or cwd in module_path.parents:
        return "source/editable checkout"
    if ".venv" in exe or "site-packages" in str(module_path):
        return "virtualenv or user Python"
    return "unknown"


def _shell_guess() -> str:
    """Return a friendly guess for the user's shell."""
    return shell_guess()


def _running_from_source() -> bool:
    """Return True when CAIROS module files live under the current checkout."""
    module_path = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    return cwd == module_path or cwd in module_path.parents


def _path_status_lines() -> list[str]:
    user_bin = _user_bin_path()
    if _path_contains(user_bin):
        return [f"PATH: ok ({user_bin} is visible)"]
    if platform.system() == "Windows":
        return [
            f"PATH: warning ({user_bin} is not on PATH)",
            "Fix for PowerShell:",
            "  py -m pipx ensurepath",
            "  restart your terminal",
        ]
    return [
        f"PATH: warning ({user_bin} is not on PATH)",
        "Fix for zsh:",
        "  echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.zshrc",
        "  source ~/.zshrc",
        "Fix for bash:",
        "  echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc",
        "  source ~/.bashrc",
    ]


def _install_info() -> str:
    """Return end-user installation diagnostics."""
    command_path = shutil.which("cairos")
    command_dir = str(Path(command_path).parent) if command_path else ""
    lines = [
        "CAIROS Install Info",
        "Package/distribution: cairos-shell",
        "Command: cairos",
        "GitHub repo: https://github.com/Saltybukket/cairos",
        f"Version: {__version__}",
        f"Platform: {platform.system() or 'unknown'}",
        f"Shell guess: {_shell_guess()}",
        f"Command path: {command_path or '<not found on PATH>'}",
        f"Python executable: {sys.executable}",
        f"Python version: {sys.version.split()[0]}",
        f"Install mode: {_install_mode()}",
        f"Running from source checkout: {'yes' if _running_from_source() else 'no'}",
        f"Source path: {Path(__file__).resolve().parents[1]}",
        f"Config path: {config_path()}",
        f"History path: {history_path()}",
        f"PATH includes command dir: {'yes' if command_dir and _path_contains(Path(command_dir)) else 'no'}",
    ]
    lines.extend(_path_status_lines())
    lines.append("Use `cairos setup` for guided setup.")
    lines.append("Use `cairos doctor` for environment diagnostics.")
    return "\n".join(lines)


def _handle_install_info() -> int:
    print(_install_info())
    return 0


def _handle_init(args: list[str]) -> int:
    if "--global" in args:
        from .config import save_config, load_config
        cfg_path = save_config(load_config())
        rules_path = init_global_rules()
        print(f"Global CAIROS config ready: {cfg_path}")
        print(f"Global CAIROS rules ready: {rules_path}")
        return 0
    path = init_local_rules()
    print(f"Project CAIROS rules ready: {path}")
    print("Use `cairos rules set <key.path> <value>` to customize templates.")
    return 0


def _handle_setup() -> int:
    print("CAIROS Setup")
    print("Package: cairos-shell")
    print("Command: cairos")
    print(f"Version: {__version__}")
    print(f"Platform: {platform.system() or 'unknown'}")
    print(f"Shell guess: {_shell_guess()}")
    print(f"Command path: {shutil.which('cairos') or '<not found on PATH>'}")
    print(f"Config path: {config_path()}")
    print(f"History path: {history_path()}")
    print(f"Project rules path: {local_rules_path()}")
    for line in _path_status_lines():
        print(line)
    print(ai_status())
    print("Behavior:")
    print("- Direct `cairos <task>` only prints a plan.")
    print("- Use `cairos run <task>` to execute after confirmation.")
    print("Recommended install:")
    print("- pipx install git+https://github.com/Saltybukket/cairos.git")
    print("Future PyPI install:")
    print("- pipx install cairos-shell")
    print("Useful next commands:")
    print("- cairos init")
    print("- cairos config ai use-ollama llama3.1")
    print("- cairos config ai use-gemini gemini-2.5-flash")
    print("- cairos config ai use-openai gpt-4.1-mini")
    print("- cairos config ai status")
    print("- cairos install-info")
    print("- cairos doctor")
    return 0


def _handle_quicksetup() -> int:
    print("CAIROS Quicksetup")
    print("")
    print("1. Install status")
    print("   package: cairos-shell")
    print("   command: cairos")
    print("   github repo: https://github.com/Saltybukket/cairos")
    print(f"   version: {__version__}")
    print(f"   command path: {shutil.which('cairos') or '<not found on PATH>'}")
    print("")
    print("2. PATH status")
    for line in _path_status_lines():
        print(f"   {line}")
    print("")
    print("3. Config locations")
    print(f"   config: {config_path()}")
    print(f"   history: {history_path()}")
    print(f"   project rules: {local_rules_path()}")
    print("")
    print("4. AI setup options")
    print("   no AI:")
    print("     cairos config ai disable")
    print("   Gemini:")
    for line in env_var_setup_hint("GEMINI_API_KEY").splitlines():
        print(f"     {line}")
    print("     cairos config ai use-gemini gemini-2.5-flash --profile gemini-flash")
    print("   Ollama:")
    print("     ollama pull llama3.1")
    print("     cairos config ai use-ollama llama3.1")
    print("")
    print("5. Try it")
    print("   cairos doctor")
    print("   cairos context")
    print("   cairos check if repo is ready to commit")
    print("")
    print("6. Install and update")
    print("   current GitHub install:")
    print("     pipx install git+https://github.com/Saltybukket/cairos.git")
    print("   update GitHub install:")
    print("     pipx uninstall cairos-shell")
    print("     pipx install git+https://github.com/Saltybukket/cairos.git")
    print("   future PyPI install after release:")
    print("     pipx install cairos-shell")
    print("   future PyPI update after release:")
    print("     pipx upgrade cairos-shell")
    return 0


COMPLETION_COMMANDS = [
    "plan", "run", "expand", "preview", "diff", "explain", "check", "context",
    "config", "rules", "doctor", "install-info", "quicksetup", "setup",
    "templates", "history", "shell", "completion", "find-dir", "init",
]


def _completion_zsh() -> str:
    words = " ".join(COMPLETION_COMMANDS)
    return f"""#compdef cairos

_cairos() {{
  local -a commands
  commands=({words})
  _describe 'cairos command' commands
}}

_cairos "$@"
"""


def _completion_powershell() -> str:
    quoted = ", ".join(f"'{command}'" for command in COMPLETION_COMMANDS)
    return f"""Register-ArgumentCompleter -Native -CommandName cairos -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @({quoted})
    $commands |
        Where-Object {{ $_ -like "$wordToComplete*" }} |
        ForEach-Object {{ [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }}
}}
"""


def _handle_completion(args: list[str]) -> int:
    if not args:
        print("Missing shell. Try: cairos completion zsh or cairos completion powershell", file=sys.stderr)
        return 1
    shell = args[0].lower()
    if shell == "zsh":
        print(_completion_zsh(), end="")
        return 0
    if shell in {"powershell", "pwsh"}:
        print(_completion_powershell(), end="")
        return 0
    print("Unsupported shell. Try: cairos completion zsh or cairos completion powershell", file=sys.stderr)
    return 1


def _templates_text(topic: str = "all") -> str:
    sections = {
        "python": [
            "Python:",
            "  cairos create python project demo with venv git pytest",
            "  cairos create requirements file",
            "  cairos add pytest",
        ],
        "cpp": [
            "C++:",
            "  cairos create cpp header Player",
            "  cairos create cpp mini project engine with class Player and main",
            "  cairos create cpp project engine with cmake",
        ],
        "git": [
            "Git:",
            "  cairos git summary",
            "  cairos check if repo is ready to commit",
            "  cairos check if repo is ready to push",
        ],
        "ai": [
            "AI:",
            "  cairos config ai use-ollama llama3.1",
            "  cairos config ai use-gemini gemini-2.5-flash",
            "  cairos config ai test",
        ],
        "system": [
            "System:",
            "  cairos show disk usage",
            "  cairos show memory usage",
            "  cairos list listening ports",
            "  cairos open project in vscode",
        ],
        "wsl": [
            "WSL:",
            "  cairos list wsl distros",
            "  cairos shutdown all wsl distros",
            "  cairos terminate the wsl distro ISP2025",
            "  cairos start the wsl distro ISP2025",
        ],
        "windows": [
            "Windows/PowerShell:",
            "  cairos open current folder in explorer",
            "  cairos show powershell version",
            "  cairos show path",
            "  cairos set gemini api key env",
        ],
        "node": [
            "Node:",
            "  cairos create node project app",
            "  cairos create package json",
            "  cairos npm install",
            "  cairos npm test",
        ],
        "rust": [
            "Rust:",
            "  cairos create rust project tool",
            "  cairos cargo build",
            "  cairos cargo test",
        ],
        "cleanup": [
            "Cleanup:",
            "  cairos clean pycache",
            "  cairos remove node_modules",
            "  cairos remove build folder",
            "  cairos clean temporary files",
        ],
        "files": [
            "Files and folders:",
            "  cairos create folder docs",
            "  cairos create file notes.txt",
            "  cairos create bash script branch_info that prints current git branch and folder",
            "  cairos create powershell script repo_info that prints current git branch and folder",
        ],
    }
    if topic in sections:
        return "\n".join(sections[topic])
    order = ["files", "python", "cpp", "node", "rust", "git", "system", "wsl", "windows", "cleanup", "ai"]
    return "CAIROS deterministic templates\n\n" + "\n\n".join("\n".join(sections[name]) for name in order)


def _handle_templates(args: list[str]) -> int:
    topic = args[0].lower() if args else "all"
    print(_templates_text(topic))
    return 0


def _handle_shell(args: list[str]) -> int:
    if args[:2] == ["install", "zsh"]:
        print("CAIROS zsh shell helper")
        print("No shell files were modified.")
        print("Optional completion install:")
        print("  mkdir -p ~/.zfunc")
        print("  cairos completion zsh > ~/.zfunc/_cairos")
        print("  echo 'fpath=(~/.zfunc $fpath)' >> ~/.zshrc")
        print("  echo 'autoload -Uz compinit && compinit' >> ~/.zshrc")
        print("")
        print("Add this optional alias snippet to ~/.zshrc if you want a tiny helper:")
        print("")
        print("# CAIROS helper")
        print("alias c='cairos'")
        print("# Try: c setup")
        return 0
    if args[:2] == ["install", "powershell"]:
        print("CAIROS PowerShell helper")
        print("No PowerShell profile was modified.")
        print("Optional completion install:")
        print("  cairos completion powershell | Out-File -Encoding utf8 $PROFILE.CurrentUserAllHosts -Append")
        print("")
        print("Optional profile snippet:")
        print("")
        print("Set-Alias c cairos")
        print("# Try: c quicksetup")
        return 0
    print("Unknown shell command. Try: cairos shell install zsh or cairos shell install powershell", file=sys.stderr)
    return 1


def _handle_history(args: list[str]) -> int:
    if args and args[0] == "clear":
        path = clear_history()
        print(f"History cleared: {path}")
        return 0
    if args and args[0] == "last":
        print(format_history(limit=1))
        return 0
    limit = 25
    if "--limit" in args:
        try:
            limit = int(args[args.index("--limit") + 1])
        except (IndexError, ValueError):
            print("Invalid --limit value.", file=sys.stderr)
            return 1
    print(format_history(limit=limit))
    return 0


def _handle_free_task(args: list[str]) -> int:
    request = _join(args)
    plan = make_plan(request)
    print(format_plan(plan))
    if not plan.steps:
        append_history(request, plan.source, plan.risk, False, 1)
        return 1
    append_history(request, plan.source, plan.risk, False, 0)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point used by the installed ``cairos`` console command."""
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        return _print_try_help()

    if args[0] in {"-h", "--help", "help"}:
        return _print_help()

    if args[0] == "--version":
        print(__version__)
        return 0

    if args[0] == "--dry-run":
        return _handle_dry_run(args[1:])

    if args[0] == "--":
        return _handle_free_task(args[1:])

    command = args[0]
    rest = args[1:]

    if command == "plan":
        return _handle_plan(rest)
    if command in {"ask", "do"}:
        return _handle_free_task(rest)
    if command == "expand":
        return _handle_expand(rest)
    if command == "run":
        return _handle_run(rest)
    if command == "preview":
        return _handle_preview(rest)
    if command == "diff":
        return _handle_diff(rest)
    if command == "check":
        return _handle_check(rest)
    if command == "explain":
        return _handle_explain(rest)
    if command == "context":
        return _handle_context(rest)
    if command == "ai":
        return _handle_config_ai(rest)
    if command == "find-dir":
        return _handle_find_dir(rest)
    if command == "config":
        return _handle_config(rest)
    if command == "rules":
        return _handle_rules(rest)
    if command == "doctor":
        return _handle_doctor()
    if command == "install-info":
        return _handle_install_info()
    if command == "quicksetup":
        return _handle_quicksetup()
    if command == "completion":
        return _handle_completion(rest)
    if command == "templates":
        return _handle_templates(rest)
    if command == "init":
        return _handle_init(rest)
    if command == "setup":
        if rest:
            return _handle_free_task(args)
        return _handle_setup()
    if command == "shell":
        return _handle_shell(rest)
    if command == "history":
        return _handle_history(rest)

    return _handle_free_task(args)


if __name__ == "__main__":
    raise SystemExit(main())
