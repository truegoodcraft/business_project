from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from core.appdb.paths import resolve_db_path

DB_PATH = resolve_db_path()


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=OFF")
        yield con
        con.commit()
    finally:
        con.close()

def _ensure_tables(con: sqlite3.Connection) -> None:
    cur = con.cursor()
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

def _get_item(con: sqlite3.Connection, item_id: int) -> Optional[Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT id, uom, qty_stored FROM items WHERE id = ?", (int(item_id),))
    r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "uom": r[1], "qty_stored": r[2]}

def _inc_qty_stored(con: sqlite3.Connection, item_id: int, delta_qty: float) -> None:
    d = int(round(delta_qty))
    con.execute("UPDATE items SET qty_stored = COALESCE(qty_stored,0) + ? WHERE id=?", (d, int(item_id)))

def purchase(item_id: int, qty: float, unit_cost_cents: int, source_kind: str = "purchase", source_id: Optional[str] = None) -> Dict[str, Any]:
    if qty <= 0:
        raise ValueError("qty must be > 0")
    with db() as con:
        _ensure_tables(con)
        if not _get_item(con, item_id):
            raise ValueError(f"item_not_found:{item_id}:{DB_PATH}")

        cur = con.cursor()
        # Batch
        cur.execute("""
            INSERT INTO item_batches(item_id, qty_initial, qty_remaining, unit_cost_cents, source_kind, source_id)
            VALUES(?,?,?,?,?,?)
        """, (int(item_id), float(qty), float(qty), int(unit_cost_cents), source_kind, source_id))
        batch_id = cur.lastrowid
        # Movement (+in)
        cur.execute("""
            INSERT INTO item_movements(item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold)
            VALUES (?,?,?,?,?,?,0)
        """, (int(item_id), batch_id, float(qty), int(unit_cost_cents), source_kind, source_id))
        # Update stock
        _inc_qty_stored(con, item_id, qty)
        return {"ok": True, "db_path": DB_PATH, "batch_id": batch_id}

def consume(item_id: int, qty: float, source_kind: str = "consume", source_id: Optional[str] = None) -> Dict[str, Any]:
    if qty <= 0:
        raise ValueError("qty must be > 0")
    with db() as con:
        _ensure_tables(con)
        if not _get_item(con, item_id):
            raise ValueError(f"item_not_found:{item_id}:{DB_PATH}")

        cur = con.cursor()
        remaining = float(qty)
        consumed: List[Dict[str, Any]] = []

        # FIFO batches with qty_remaining > 0
        cur.execute("""
            SELECT id, qty_remaining, unit_cost_cents
            FROM item_batches
            WHERE item_id=? AND qty_remaining > 0
            ORDER BY created_at ASC, id ASC
        """, (int(item_id),))
        rows = cur.fetchall()

        for bid, qty_rem, cost in rows:
            if remaining <= 0:
                break
            take = min(remaining, float(qty_rem))
            # create movement row per batch
            cur.execute("""
                INSERT INTO item_movements(item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold)
                VALUES (?,?,?,?,?,?,0)
            """, (int(item_id), bid, -take, int(cost), source_kind, source_id))
            # update batch remaining
            cur.execute("UPDATE item_batches SET qty_remaining = qty_remaining - ? WHERE id=?", (take, bid))
            consumed.append({"batch_id": bid, "qty": take, "unit_cost_cents": int(cost)})
            remaining -= take

        # oversold portion (no batches left)
        oversold_qty = max(0.0, remaining)
        if oversold_qty > 0:
            cur.execute("""
                INSERT INTO item_movements(item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold)
                VALUES (NULL, NULL, ?, 0, ?, ?, 1)
            """, (-oversold_qty, source_kind, source_id))
            consumed.append({"batch_id": None, "qty": oversold_qty, "unit_cost_cents": 0})

        # update stock (negative)
        _inc_qty_stored(con, item_id, -qty)

        total_cost_cents = sum(int(c["unit_cost_cents"]) * float(c["qty"]) for c in consumed if c["unit_cost_cents"] is not None)
        return {"ok": True, "db_path": DB_PATH, "consumed": consumed, "qty": qty, "total_cost_cents": int(round(total_cost_cents))}

def valuation(item_id: Optional[int] = None) -> Dict[str, Any]:
    with db() as con:
        _ensure_tables(con)
        cur = con.cursor()
        if item_id is not None:
            cur.execute("""
                SELECT COALESCE(SUM(qty_remaining * unit_cost_cents),0)
                FROM item_batches WHERE item_id=?
            """, (int(item_id),))
            total = int(round(cur.fetchone()[0] or 0))
            return {"item_id": item_id, "total_value_cents": total}
        else:
            cur.execute("""
                SELECT item_id, COALESCE(SUM(qty_remaining * unit_cost_cents),0) as total
                FROM item_batches GROUP BY item_id
            """)
            rows = cur.fetchall()
            return {"totals": [{"item_id": r[0], "total_value_cents": int(round(r[1] or 0))} for r in rows]}

def list_movements(item_id: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    with db() as con:
        _ensure_tables(con)
        cur = con.cursor()
        if item_id is not None:
            cur.execute("""
                SELECT id, item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold, created_at
                FROM item_movements
                WHERE item_id=?
                ORDER BY id DESC
                LIMIT ?
            """, (int(item_id), int(limit)))
        else:
            cur.execute("""
                SELECT id, item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold, created_at
                FROM item_movements
                ORDER BY id DESC
                LIMIT ?
            """, (int(limit),))
        cols = [c[0] for c in cur.description]
        data = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"movements": data}
