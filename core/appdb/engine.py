from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.appdb.paths import app_db_path

# Resolve and ensure the directory exists BEFORE creating the engine
DB_PATH: Path = app_db_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# On Windows the correct file URL is exactly 3 slashes before the absolute path.
# Example: sqlite+pysqlite:///C:/Users/you/AppData/Local/BUSCore/app/app.db
DB_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"

ENGINE = create_engine(
    DB_URL,
    future=True,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)

# Startup visibility for logs
try:
    with ENGINE.connect() as conn:
        rows = conn.execute(text("PRAGMA database_list;")).all()
        print(f"[DB] Using: {DB_PATH}  exists={DB_PATH.exists()}  url={ENGINE.url!s}  pragma={rows}")
except Exception as e:
    print(f"[DB] Engine initialization check failed: {e!r}")
