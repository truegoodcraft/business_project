from __future__ import annotations

import os
from pathlib import Path

# Canonical Windows location. No repo-local fallback.
# Example: %LOCALAPPDATA%\BUSCore\app\app.db
_APP_ROOT = Path(os.getenv("LOCALAPPDATA", "")) / "BUSCore"
APP_DIR = _APP_ROOT / "app"
STATE_DIR = APP_DIR / "state"
DATA_DIR = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR = DATA_DIR / "imports"
UI_DIR = APP_DIR / "ui"
DB_PATH = APP_DIR / "app.db"

# Ensure folders exist on import (first run)
for d in (APP_DIR, STATE_DIR, DATA_DIR, JOURNALS_DIR, IMPORTS_DIR, UI_DIR):
    d.mkdir(parents=True, exist_ok=True)

def app_db_path() -> Path:
    """Return the canonical SQLite DB path in AppData."""
    return DB_PATH

# -------------------------------
# Back-compat shims (do not remove)
# Some legacy modules import these names.
def app_data_dir() -> Path:
    return APP_DIR

def state_dir() -> Path:
    return STATE_DIR

def secrets_dir() -> Path:
    # sibling of "app": %LOCALAPPDATA%\BUSCore\secrets
    return _APP_ROOT / "secrets"
# -------------------------------
