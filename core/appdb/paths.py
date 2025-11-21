from pathlib import Path
import os

# Canonical base on Windows: %LOCALAPPDATA%\BUSCore\app
_LOCAL = os.getenv("LOCALAPPDATA") or ""
BUS_ROOT = Path(_LOCAL) / "BUSCore" / "app"

APP_DIR      = BUS_ROOT
DATA_DIR     = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR  = DATA_DIR / "imports"
STATE_DIR    = APP_DIR / "state"
DB_PATH      = APP_DIR / "app.db"

# Ensure folders exist (first run friendly)
for d in (APP_DIR, DATA_DIR, JOURNALS_DIR, IMPORTS_DIR, STATE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Back-compat & public API ----
def state_dir() -> Path:      # imported by capabilities.registry
    return STATE_DIR

def app_db_path() -> Path:
    return DB_PATH

def ui_dir() -> Path:         # serve UI from repo
    return Path(__file__).resolve().parent.parent / "ui"

__all__ = [
    "BUS_ROOT", "APP_DIR", "DATA_DIR", "JOURNALS_DIR", "IMPORTS_DIR", "STATE_DIR",
    "DB_PATH", "state_dir", "app_db_path", "ui_dir",
]
