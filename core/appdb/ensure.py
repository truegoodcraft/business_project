from __future__ import annotations
import os
import sqlite3, time
from contextlib import contextmanager
from typing import Dict, Any

from core.appdb.paths import resolve_db_path

DB_PATH = resolve_db_path()

@contextmanager
def conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
    finally:
        con.commit(); con.close()

def ensure_schema() -> Dict[str, Any]:
    """
    v1 baseline schema (no legacy qty/unit in DB).
    Canonical stock = items.qty_stored (+ items.uom).
    Safe to run on every startup.
    """
    created = {"items": False, "item_batches": False, "item_movements": False}

    with conn() as con:
        cur = con.cursor()

        # ITEMS (no qty/unit legacy cols)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
        if not cur.fetchone():
            cur.execute("""
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                vendor_id INTEGER,
                sku TEXT,
                name TEXT NOT NULL,
                uom TEXT NOT NULL DEFAULT 'ea',          -- 'ea','g','mm','mm2','mm3'
                qty_stored INTEGER NOT NULL DEFAULT 0,   -- canonical on-hand (int)
                price REAL DEFAULT 0,
                notes TEXT,
                item_type TEXT,
                location TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            created["items"] = True

        # ITEM BATCHES (cost layers)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_batches'")
        if not cur.fetchone():
            cur.execute("""
            CREATE TABLE item_batches (
                id INTEGER PRIMARY KEY,
                item_id INTEGER NOT NULL REFERENCES items(id),
                qty_initial REAL NOT NULL,
                qty_remaining REAL NOT NULL,
                unit_cost_cents INTEGER NOT NULL,
                source_kind TEXT NOT NULL,
                source_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            created["item_batches"] = True

        # MOVEMENTS (physical ledger)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_movements'")
        if not cur.fetchone():
            cur.execute("""
            CREATE TABLE item_movements (
                id INTEGER PRIMARY KEY,
                item_id INTEGER NOT NULL REFERENCES items(id),
                batch_id INTEGER REFERENCES item_batches(id),
                qty_change REAL NOT NULL,                  -- +in / -out (physical)
                unit_cost_cents INTEGER DEFAULT 0,         -- snapshot
                source_kind TEXT NOT NULL,
                source_id TEXT,
                is_oversold BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            created["item_movements"] = True

    return {"ok": True, "path": DB_PATH, "created": created, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}

if __name__ == "__main__":
    print(ensure_schema())
