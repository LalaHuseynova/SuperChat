#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv: https://docs.astral.sh/uv/getting-started/installation/'
  exit 1
fi
if [[ "${1:-}" == "--vision" ]]; then
  exec uv run --extra vision uvicorn superchat.app:app --host 127.0.0.1 --port "${PORT:-8000}"
fi
exec uv run uvicorn superchat.app:app --host 127.0.0.1 --port "${PORT:-8000}"
