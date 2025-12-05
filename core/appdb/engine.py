from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.appdb.paths import resolve_db_path  # SoT path helper

# --- Path & URL -------------------------------------------------------------

DB_PATH: Path = Path(resolve_db_path())
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DB_SOURCE = "ENV" if os.environ.get("BUS_DB") else "APPDATA"
print(f"[db] BUS_DB ({DB_SOURCE}) -> {DB_PATH}")


def _sqlite_url(p: Path) -> str:
    """Windows-safe sqlite+pysqlite URL with exactly 3 slashes.

    Example:
      C:/Users/me/AppData/Local/BUSCore/app/app.db
      -> sqlite+pysqlite:///C:/Users/me/AppData/Local/BUSCore/app/app.db
    """
    posix = p.resolve().as_posix()
    # If it starts with a drive letter, leave it; otherwise strip leading slashes.
    if re.match(r"^[A-Za-z]:/", posix):
        return f"sqlite+pysqlite:///{posix}"
    return f"sqlite+pysqlite:///{posix}"


DB_URL = _sqlite_url(DB_PATH)

# --- Engine & Session -------------------------------------------------------

ENGINE = create_engine(DB_URL, future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE, future=True)


def get_session() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Debug helper (used by /dev/db/where) -----------------------------------


def debug_db_where() -> dict:
    resolved = str(DB_PATH.resolve())
    pragma = []
    with ENGINE.connect() as conn:
        try:
            pragma = list(conn.execute(text("PRAGMA database_list")))
        except Exception:
            pragma = []
    return {
        "engine_url": DB_URL,
        "database": DB_PATH.as_posix(),
        "resolved_fs_path": resolved,
        "pragma": [tuple(row) for row in pragma],
    }


# Optional boot log if explicitly enabled
if os.getenv("BUSCORE_DEBUG_DB", "0") in ("1", "true", "yes", "on"):
    info = debug_db_where()
    print(f"[DB] Using: {info['resolved_fs_path']}  url={info['engine_url']}  pragma={info.get('pragma')}")
