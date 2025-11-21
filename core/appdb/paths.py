from pathlib import Path
import os

APP_DIR   = Path(os.getenv("LOCALAPPDATA", "")) / "BUSCore" / "app"
STATE_DIR = APP_DIR / "state"


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_dir() -> Path:
    return ensure_dir(APP_DIR)


def state_dir() -> Path:
    r"""Returns %LOCALAPPDATA%\\BUSCore\\app\\state and ensures it exists."""
    return ensure_dir(STATE_DIR)


def app_db_path() -> Path:
    p = APP_DIR / "app.db"
    ensure_dir(p.parent)
    return p

DB_PATH = app_db_path()

# Back-compat shims (used by older modules)
def app_data_dir() -> Path: return app_dir()
def secrets_dir()  -> Path: return APP_DIR.parent / "secrets"
def ui_dir() -> Path:
    # Serve UI from repo (not AppData)
    return Path(__file__).resolve().parents[2] / "core" / "ui"

# Additional convenience paths
DATA_DIR = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR = DATA_DIR / "imports"
UI_DIR = ui_dir()
