import os
import pathlib


def app_data_dir() -> pathlib.Path:
    p = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_db_path() -> pathlib.Path:
    return app_data_dir() / "app.db"
