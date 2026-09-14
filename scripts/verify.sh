#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
action_python="${DCL_ACTION_PYTHON:-python3}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  "$action_python" -m unittest discover -s tests -v
"$action_python" -m ruff check --config pyproject.toml src tests
"$action_python" -m ruff format --check src tests
"$action_python" -m build --wheel --outdir dist .
"$action_python" -m pip check
