#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v uv >/dev/null 2>&1; then
  echo 'Install uv: https://docs.astral.sh/uv/getting-started/installation/'
  exit 1
fi
# Keep the array nonempty: Bash 3.2 treats empty arrays as unset with nounset.
uv_args=(run)
for arg in "$@"; do
  case "$arg" in
    --vision) uv_args+=(--extra vision) ;;
    --real) export SUPERCHAT_DATA_MODE=database; uv_args+=(--extra scraper --extra vision) ;;
    --snapshot) export SUPERCHAT_DATA_MODE=snapshot ;;
    --mock) export SUPERCHAT_DATA_MODE=mock ;;
    *) echo "Usage: ./run.sh [--real|--snapshot|--mock] [--vision]"; exit 1 ;;
  esac
done
exec uv "${uv_args[@]}" uvicorn superchat.app:app --host 127.0.0.1 --port "${PORT:-8000}"
