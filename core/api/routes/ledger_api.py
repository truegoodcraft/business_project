# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3

from core.ledger.fifo import purchase as fifo_purchase, consume as fifo_consume, valuation as fifo_valuation, list_movements as fifo_list
from core.appdb.paths import resolve_db_path
from core.api.utils.devguard import require_dev
from core.appdb.engine import get_session
from sqlalchemy.orm import Session
from core.appdb.ledger import on_hand_qty, fifo_consume as sa_fifo_consume, add_batch

# NOTE: Router prefix is "/ledger"; child paths must not repeat "/ledger" to avoid
# duplicate segments (e.g., /app/ledger/adjust).
router = APIRouter(prefix="/ledger", tags=["ledger"])
DB_PATH = resolve_db_path()

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


class PurchaseIn(BaseModel):
    item_id: int
    qty: float = Field(gt=0)
    unit_cost_cents: int = Field(ge=0)
    source_kind: str = "purchase"
    source_id: Optional[str] = None


@router.post("/purchase")
def purchase(body: PurchaseIn):
    try:
        return fifo_purchase(body.item_id, body.qty, body.unit_cost_cents, body.source_kind, body.source_id)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("item_not_found:"):
            _, item_id, path = msg.split(":", 2)
            raise HTTPException(status_code=404, detail={"reason": "item_not_found", "item_id": int(item_id), "db_path": path})
        raise


class ConsumeIn(BaseModel):
    item_id: int
    qty: float = Field(gt=0)
    source_kind: str = "consume"
    source_id: Optional[str] = None


@router.post("/consume")
def consume(body: ConsumeIn):
    try:
        return fifo_consume(body.item_id, body.qty, body.source_kind, body.source_id)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("item_not_found:"):
            _, item_id, path = msg.split(":", 2)
            raise HTTPException(status_code=404, detail={"reason": "item_not_found", "item_id": int(item_id), "db_path": path})
        raise


# -------------------------
# POST /app/ledger/adjust
# -------------------------
class AdjustmentInput(BaseModel):
    item_id: int
    qty_change: float = Field(..., ne=0)
    note: str | None = None


@router.post("/adjust")
def adjust_stock(body: AdjustmentInput, db: Session = Depends(get_session)):
    """
    Positive adjustment:
      - create a new batch with qty_remaining=+N and unit_cost_cents=0
      - write a matching positive movement
    Negative adjustment:
      - consume FIFO from existing batches
      - 400 if insufficient on-hand; no partials
    """
    if body.qty_change > 0:
        add_batch(db, body.item_id, body.qty_change, unit_cost_cents=0, source_kind="adjustment", source_id=None)
        db.commit()
        return {"ok": True}
    need = abs(body.qty_change)
    on_hand = on_hand_qty(db, body.item_id)
    if on_hand + 1e-9 < need:
        raise HTTPException(status_code=400, detail="insufficient stock for negative adjustment")
    sa_fifo_consume(db, body.item_id, need, source_kind="adjustment", source_id=None)
    db.commit()
    return {"ok": True}


@router.get("/valuation")
def valuation(item_id: Optional[int] = None):
    return fifo_valuation(item_id)


@router.get("/movements")
def movements(item_id: Optional[int] = None, limit: int = 100):
    return fifo_list(item_id, limit)


@router.get("/debug/db")
def ledger_debug(item_id: int | None = None):
    require_dev()
    path = resolve_db_path()
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='items'")
        has_items = bool(cur.fetchone()[0])
        item_row = None
        items_count = None
        if has_items:
            cur.execute("SELECT COUNT(*) FROM items")
            items_count = int(cur.fetchone()[0])
            if item_id is not None:
                cur.execute("SELECT id,name,sku,uom,qty_stored FROM items WHERE id=?", (int(item_id),))
                item_row = cur.fetchone()
    return {"db_path": path, "has_items": has_items, "items_count": items_count, "item_row": item_row}
