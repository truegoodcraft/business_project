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

# --- Back-compat: some modules still import secrets_dir() ---
from pathlib import Path as _Path  # no-op if already imported

def secrets_dir() -> _Path:
    """Return %LOCALAPPDATA%\BUSCore\secrets (sibling of 'app')."""
    p = APP_DIR.parent / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p

# expose via __all__ if present
try:
    __all__
except NameError:
    __all__ = []
if "secrets_dir" not in __all__:
    __all__.append("secrets_dir")
# --- Back-compat shims for legacy callers (tgc/bootstrap_fs.py, etc.) ---
from pathlib import Path as _Path  # safe if already imported

def app_data_dir() -> _Path:
    """Returns %LOCALAPPDATA%\BUSCore\app"""
    return APP_DIR

def secrets_dir() -> _Path:
    """Returns %LOCALAPPDATA%\BUSCore\secrets (sibling of 'app') and ensures it exists."""
    p = APP_DIR.parent / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p

def state_dir() -> _Path:
    """Returns %LOCALAPPDATA%\BUSCore\app\state and ensures it exists."""
    p = APP_DIR / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p

# expose via __all__ if present
try:
    __all__
except NameError:
    __all__ = []
for _n in ("app_data_dir", "secrets_dir", "state_dir"):
    if _n not in __all__:
        __all__.append(_n)
