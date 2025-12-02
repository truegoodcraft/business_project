from __future__ import annotations
import os, sqlite3, time
from contextlib import contextmanager
from typing import Set

DB_PATH = os.environ.get("BUS_DB", "data/app.db")

@contextmanager
def conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
    finally:
        con.commit()
        con.close()

def table_exists(name: str) -> bool:
    with conn() as con:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
        return cur.fetchone() is not None

def get_columns(name: str) -> Set[str]:
    with conn() as con:
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({name})")
        return {row[1] for row in cur.fetchall()}

def ensure_items_columns() -> dict:
    """
    Idempotently ensure items.uom (TEXT NOT NULL DEFAULT 'ea') and
    items.qty_stored (INTEGER NOT NULL DEFAULT 0) exist.
    """
    if not table_exists("items"):
        return {"ok": False, "reason": "items table not found", "path": DB_PATH}

    cols = get_columns("items")
    changed = False
    with conn() as con:
        cur = con.cursor()
        if "uom" not in cols:
            cur.execute("ALTER TABLE items ADD COLUMN uom TEXT NOT NULL DEFAULT 'ea'")
            changed = True
        if "qty_stored" not in cols:
            cur.execute("ALTER TABLE items ADD COLUMN qty_stored INTEGER NOT NULL DEFAULT 0")
            changed = True

    return {"ok": True, "changed": changed, "path": DB_PATH, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}

if __name__ == "__main__":
    out = ensure_items_columns()
    print(out)
