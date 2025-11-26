#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "[launch] Creating venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ "${BUSCORE_EXTRAS:-0}" = "1" ] && [ -f requirements-extras.txt ]; then
  echo "[launch] Installing extras..."
  pip install -r requirements-extras.txt
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
echo "[launch] Starting BUS Core at http://$HOST:$PORT"
python -c "import uvicorn; uvicorn.run('tgc.http:app', host='$HOST', port=int('$PORT'), log_level='info')"
