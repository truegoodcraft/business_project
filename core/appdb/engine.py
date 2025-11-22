from __future__ import annotations
from sqlalchemy import create_engine, text
from core.appdb.paths import app_db_path
from pathlib import Path

DB_PATH: Path = app_db_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Build a correct 3-slash SQLite URL using POSIX separators.
DB_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"

ENGINE = create_engine(DB_URL, future=True, connect_args={"check_same_thread": False})


def db_debug_info() -> dict:
    disk = None
    try:
        with ENGINE.connect() as conn:
            rows = conn.execute(text("PRAGMA database_list")).all()
            # rows: [(seq, name, file)]
            disk = [tuple(r) for r in rows]
    except Exception as e:
        disk = [("error", "PRAGMA database_list failed", str(e))]
    return {
        "engine_url": str(ENGINE.url),
        "database": ENGINE.url.database if getattr(ENGINE.url, "database", None) else str(DB_PATH),
        "configured_path": str(DB_PATH),
        "pragma_database_list": disk,
        "exists_on_fs": DB_PATH.exists(),
    }
