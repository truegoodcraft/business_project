from pathlib import Path
import os

_local_appdata = os.environ.get("LOCALAPPDATA")
if _local_appdata:
    _default_root = Path(_local_appdata) / "BUSCore" / "app"
else:
    _default_root = Path.home() / "AppData" / "Local" / "BUSCore" / "app"

BUS_ROOT = Path(os.environ.get("BUS_ROOT") or _default_root).resolve()

APP_DIR = BUS_ROOT
DATA_DIR = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR = DATA_DIR / "imports"

for d in (DATA_DIR, JOURNALS_DIR, IMPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "app.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Prefer repo UI when BUS_ROOT points to project root
DEV_UI_DIR = APP_DIR / "core" / "ui"
DEFAULT_UI_DIR = APP_DIR / "ui"
UI_DIR = DEV_UI_DIR if DEV_UI_DIR.joinpath("shell.html").exists() else DEFAULT_UI_DIR
