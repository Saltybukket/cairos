"""Server entry points for ``cairos gui``."""

from __future__ import annotations

import importlib.util
import socket
import webbrowser
from dataclasses import dataclass

from ..config import config_path
from .security import generate_session_token, is_local_host
from .state import load_gui_state


GUI_DEPENDENCIES = {
    "FastAPI": "fastapi",
    "Uvicorn": "uvicorn",
    "Jinja2": "jinja2",
    "python-multipart": "multipart",
}


@dataclass(frozen=True)
class GuiCheck:
    ok: bool
    lines: list[str]


def dependency_status() -> dict[str, bool]:
    return {label: importlib.util.find_spec(module) is not None for label, module in GUI_DEPENDENCIES.items()}


def missing_dependency_message() -> str:
    return """CAIROS GUI dependencies are not installed.

Install with:
  pipx inject cairos-shell fastapi uvicorn jinja2 python-multipart

or, when available from PyPI:
  pipx install "cairos-shell[gui]"

For editable/dev install:
  python -m pip install -e ".[gui]"
"""


def check_gui_support() -> GuiCheck:
    deps = dependency_status()
    lines = ["CAIROS GUI check:"]
    lines.extend(f"{name}: {'available' if ok else 'missing'}" for name, ok in deps.items())
    try:
        state = load_gui_state()
        lines.append("Config readable: yes")
        lines.append(f"Profiles loaded: {len(state.profiles)}")
        lines.append("GUI state: ok")
    except Exception as exc:
        lines.append(f"Config readable: no ({exc.__class__.__name__})")
        lines.append("GUI state: error")
        return GuiCheck(False, lines)
    return GuiCheck(all(deps.values()), lines)


def _choose_port(host: str, port: int) -> int:
    if port != 0:
        return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def run_gui(host: str = "127.0.0.1", port: int = 0, no_open: bool = False, debug: bool = False) -> int:
    if not is_local_host(host):
        print("Refusing to bind CAIROS GUI to a non-local host.")
        print("Use 127.0.0.1 or localhost.")
        return 1
    check = check_gui_support()
    if not check.ok:
        print(missing_dependency_message())
        print("\n".join(check.lines))
        return 1

    from uvicorn import Config, Server

    from .app import create_app

    token = generate_session_token()
    chosen_port = _choose_port(host, port)
    url = f"http://{host}:{chosen_port}/?token={token}"
    app = create_app(token, debug=debug)
    print("CAIROS GUI running locally:")
    print(f"  {url}")
    print("")
    print("Config:")
    print(f"  {config_path()}")
    print("")
    print("Security:")
    print("  Bound to localhost only. POST actions require a temporary session token.")
    print("  Raw API keys are never displayed or stored by CAIROS.")
    print("")
    print("Press Ctrl+C to stop.")
    if not no_open:
        webbrowser.open(url)
    server = Server(Config(app=app, host=host, port=chosen_port, log_level="debug" if debug else "warning"))
    server.run()
    return 0


def handle_gui_command(args: list[str]) -> int:
    host = "127.0.0.1"
    port = 0
    no_open = False
    debug = False
    check_only = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-h", "--help", "help"}:
            print("Usage: cairos gui [--host 127.0.0.1] [--port 0] [--no-open] [--debug] [--check]")
            print("")
            print("Starts the optional local FastAPI/HTMX GUI. The server binds only to localhost.")
            print("--check runs dependency/state diagnostics and exits.")
            return 0
        if arg == "--check":
            check_only = True
            index += 1
            continue
        if arg == "--host" and index + 1 < len(args):
            host = args[index + 1]
            index += 2
            continue
        if arg == "--port" and index + 1 < len(args):
            try:
                port = int(args[index + 1])
            except ValueError:
                print("Invalid --port value.")
                return 1
            index += 2
            continue
        if arg == "--no-open":
            no_open = True
            index += 1
            continue
        if arg == "--debug":
            debug = True
            index += 1
            continue
        print(f"Unknown gui option: {arg}")
        return 1
    if not is_local_host(host):
        print("Refusing to bind CAIROS GUI to a non-local host.")
        print("Use 127.0.0.1 or localhost.")
        return 1
    if check_only:
        check = check_gui_support()
        print("\n".join(check.lines))
        return 0 if check.ok else 1
    return run_gui(host=host, port=port, no_open=no_open, debug=debug)
