from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from core.appdb.paths import app_db_path

DB_PATH: Path = app_db_path()
# Use forward slashes for URL safety on Windows
DB_URL = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"

ENGINE = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autocommit=False, autoflush=False)

# Startup log
print(f"[DB] Using SQLite at: {DB_PATH} (url={DB_URL})")
