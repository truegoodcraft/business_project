import sqlite3
import time

from .paths import app_db_path

SCHEMA_VERSION = 1

DDL = [
    """
CREATE TABLE IF NOT EXISTS vendors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  contact TEXT,
  notes TEXT,
  created_at TEXT NOT NULL
);
""",
    """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
  sku TEXT,
  name TEXT NOT NULL,
  qty REAL NOT NULL DEFAULT 0,
  unit TEXT DEFAULT 'ea',
  price REAL,
  notes TEXT,
  created_at TEXT NOT NULL
);
""",
    """
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER REFERENCES items(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo', -- todo|doing|done
  due TEXT,
  notes TEXT,
  created_at TEXT NOT NULL
);
""",
    """
CREATE TABLE IF NOT EXISTS attachments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL, -- 'vendor'|'item'|'task'
  entity_id INTEGER NOT NULL,
  reader_id TEXT NOT NULL,   -- opaque Reader ID (e.g., local:<sig>:<b64>)
  label TEXT,
  created_at TEXT NOT NULL
);
"""
]


def connect():
    return sqlite3.connect(
        app_db_path(), detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )


def init_db():
    con = connect()
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    cur = con.execute("PRAGMA user_version;")
    v = cur.fetchone()[0]
    if v < SCHEMA_VERSION:
        for ddl in DDL:
            con.executescript(ddl)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION};")
    con.commit()
    con.close()


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
