# Installing CAIROS

CAIROS is a normal Python console command. It works from any project directory
after installation. The PyPI package name is `cairos-shell`; the terminal
command is still `cairos`.

## Recommended: pipx

```bash
pipx install cairos-shell
cairos setup
```

This installs CAIROS once as a user-level shell tool. You do not need to manage
virtual environments or know where pipx stores the package.

## Development Checkout

```bash
git clone <repo-url>
cd cairos
pipx install --editable .
cairos install-info
```

## GitHub Install

```bash
pipx install git+https://github.com/<user>/<repo>.git
```

## Fallback Without pipx

```bash
python -m pip install --user cairos-shell
```

If `cairos` is not found after this, make sure `~/.local/bin` is on `PATH`.

## Validate

```bash
cairos --version
cairos install-info
cairos doctor
cairos context
```

Uninstall/reset:

```bash
python -m pip uninstall cairos-shell
rm -rf ~/.config/cairos ~/.local/state/cairos
```
