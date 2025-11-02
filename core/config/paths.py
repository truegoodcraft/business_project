from pathlib import Path
import os

if "LOCALAPPDATA" not in os.environ:
    os.environ["LOCALAPPDATA"] = str(Path.home() / "AppData" / "Local")

BUS_ROOT = Path(
    os.environ.get("BUS_ROOT")
    or (Path(os.environ["LOCALAPPDATA"]) / "BUSCore" / "app")
).resolve()

APP_DIR = BUS_ROOT
DATA_DIR = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR = DATA_DIR / "imports"

for d in (DATA_DIR, JOURNALS_DIR, IMPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "app.db"
DB_URL = f"sqlite:///{DB_PATH}"

# UI location
DEV_UI_DIR = APP_DIR / "core" / "ui"
DEFAULT_UI_DIR = APP_DIR / "ui"
UI_DIR = DEV_UI_DIR if DEV_UI_DIR.joinpath("shell.html").exists() else DEFAULT_UI_DIR
