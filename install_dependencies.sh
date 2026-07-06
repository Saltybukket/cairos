#!/usr/bin/env sh
set -eu

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo "CAIROS installed in .venv"
echo "Run: . .venv/bin/activate && cairos doctor"
