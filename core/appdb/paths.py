from pathlib import Path
import os


def app_db_path() -> Path:
    """
    Canonical working DB path (Windows-only):
    %LOCALAPPDATA%\BUSCore\app\app.db
    """
    root = Path(os.getenv("LOCALAPPDATA", "")) / "BUSCore" / "app"
    root.mkdir(parents=True, exist_ok=True)  # ensure folder exists
    return root / "app.db"
