from fastapi import APIRouter
import os, sqlite3

router = APIRouter(prefix="/app/ledger", tags=["ledger"])
DB_PATH = os.environ.get("BUS_DB", "data/app.db")

def _has_items_qty_stored() -> bool:
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
        if not cur.fetchone():
            return False
        cur.execute("PRAGMA table_info(items)")
        cols = {r[1] for r in cur.fetchall()}
        return "qty_stored" in cols
    finally:
        con.close()

@router.get("/health")
def health():
    if not _has_items_qty_stored():
        return {"desync": True, "problems": [{"reason": "items.qty_stored missing"}]}
    return {"desync": False, "note": "Using items.qty_stored for on-hand checks"}

@router.post("/bootstrap")
def bootstrap_legacy():
    if not _has_items_qty_stored():
        return {"created": 0, "error": "items.qty_stored missing"}
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS item_batches(
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            qty_initial REAL NOT NULL,
            qty_remaining REAL NOT NULL,
            unit_cost_cents INTEGER NOT NULL,
            source_kind TEXT NOT NULL,
            source_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS item_movements(
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            batch_id INTEGER,
            qty_change REAL NOT NULL,
            unit_cost_cents INTEGER DEFAULT 0,
            source_kind TEXT NOT NULL,
            source_id TEXT,
            is_oversold BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")

        cur.execute("SELECT id, qty_stored FROM items WHERE COALESCE(qty_stored,0) > 0")
        rows = cur.fetchall()
        created = 0
        for item_id, onhand in rows:
            cur.execute("SELECT 1 FROM item_batches WHERE item_id=? AND source_kind='legacy_migration' LIMIT 1", (item_id,))
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO item_batches(item_id, qty_initial, qty_remaining, unit_cost_cents, source_kind, source_id)
                VALUES (?, ?, ?, 0, 'legacy_migration', ?)
            """, (item_id, float(onhand), float(onhand), f"legacy:{item_id}"))
            batch_id = cur.lastrowid
            cur.execute("""
                INSERT INTO item_movements(item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold)
                VALUES (?, ?, ?, 0, 'legacy_migration', ?, 0)
            """, (item_id, batch_id, float(onhand), f"legacy:{item_id}"))
            created += 1

        con.commit()
        return {"created": created, "using": "qty_stored"}
    finally:
        con.close()
