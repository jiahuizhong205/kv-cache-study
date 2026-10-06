#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  printf '%s\n' "Python environment not found: $PYTHON_BIN" >&2
  printf '%s\n' 'For previews: uv venv --python 3.12 .venv-checks; set PYTHON_BIN to its bin/python.' >&2
  exit 2
fi
exec "$PYTHON_BIN" "$ROOT/scripts/runner.py" "$@"
