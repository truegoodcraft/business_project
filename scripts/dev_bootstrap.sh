#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  # Always core; extras only if requested via BUSCORE_EXTRAS=1
  pip install -r requirements.txt
  if [ "${BUSCORE_EXTRAS:-0}" = "1" ] && [ -f requirements-extras.txt ]; then
    pip install -r requirements-extras.txt
  fi
else
  pip install fastapi uvicorn pydantic pydantic-settings platformdirs sqlalchemy python-multipart
fi
