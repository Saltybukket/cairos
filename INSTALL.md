# Installing CAIROS

CAIROS is a normal Python console command. It works from any project directory
after installation.

Development checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make test
```

User-level install:

```bash
pipx install .
```

Basic validation:

```bash
cairos --version
cairos doctor
cairos context
```

Uninstall/reset:

```bash
python -m pip uninstall cairos
rm -rf ~/.config/cairos ~/.local/state/cairos
```
