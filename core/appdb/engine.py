from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.appdb.paths import app_db_path

# Resolve the canonical DB path and ensure directory exists BEFORE engine creation.
DB_PATH: Path = app_db_path()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Use an absolute URL; as_posix avoids backslash escaping issues on Windows.
DB_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"

# Single shared engine/session factory for the app.
ENGINE = create_engine(
    DB_URL,
    future=True,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)
