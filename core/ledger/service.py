# core/ledger/service.py
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import sqlite3, os, math, json, time

DB_PATH = os.environ.get("BUS_DB", "data/app.db")

# Utility

def _conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH)

@dataclass
class MovementResult:
    item_id: int
    total_qty: float
    lines: List[Dict]

# Public API

def stock_in(item_id: int, qty_in: float, unit_cost_cents: int, source_kind: str, source_id: Optional[str] = None) -> MovementResult:
    assert qty_in >= 0, "qty_in must be >= 0"
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO item_batches (item_id, qty_initial, qty_remaining, unit_cost_cents, source_kind, source_id) VALUES (?,?,?,?,?,?)",
            (item_id, qty_in, qty_in, unit_cost_cents, source_kind, source_id)
        )
        batch_id = cur.lastrowid
        cur.execute(
            "INSERT INTO item_movements (item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold) VALUES (?,?,?,?,?,?,0)",
            (item_id, batch_id, qty_in, unit_cost_cents, source_kind, source_id)
        )
        return MovementResult(item_id=item_id, total_qty=qty_in, lines=[{"batch_id": batch_id, "qty": qty_in, "unit_cost_cents": unit_cost_cents}])


def stock_out_fifo(item_id: int, qty_out: float, source_kind: str, source_id: Optional[str] = None) -> MovementResult:
    assert qty_out >= 0, "qty_out must be >= 0"
    remaining = qty_out
    lines: List[Dict] = []
    with _conn() as con:
        cur = con.cursor()
        # Fetch open batches FIFO
        cur.execute(
            "SELECT id, qty_remaining, unit_cost_cents FROM item_batches WHERE item_id=? AND qty_remaining > 0 ORDER BY created_at, id",
            (item_id,)
        )
        for bid, qty_rem, ucc in cur.fetchall():
            if remaining <= 0: break
            take = min(remaining, float(qty_rem))
            if take <= 0: continue
            # movement
            cur.execute(
                "INSERT INTO item_movements (item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold) VALUES (?,?,?,?,?,?,0)",
                (item_id, bid, -take, ucc, source_kind, source_id)
            )
            # update batch
            cur.execute("UPDATE item_batches SET qty_remaining = qty_remaining - ? WHERE id=?", (take, bid))
            lines.append({"batch_id": bid, "qty": -take, "unit_cost_cents": ucc})
            remaining -= take
        # Oversold remainder
        if remaining > 0:
            cur.execute(
                "INSERT INTO item_movements (item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold) VALUES (?,?,?,?,?,?,1)",
                (item_id, None, -remaining, 0, source_kind, source_id)
            )
            lines.append({"batch_id": None, "qty": -remaining, "unit_cost_cents": 0, "oversold": True})
    return MovementResult(item_id=item_id, total_qty=-qty_out, lines=lines)


def valuation(item_id: Optional[int] = None) -> Dict:
    with _conn() as con:
        cur = con.cursor()
        if item_id is None:
            cur.execute("SELECT SUM(qty_remaining * unit_cost_cents) FROM item_batches")
            total_cents = int(cur.fetchone()[0] or 0)
            return {"total_cents": total_cents, "display": f"{total_cents/100:.2f}"}
        else:
            cur.execute("SELECT SUM(qty_remaining * unit_cost_cents) FROM item_batches WHERE item_id=?", (item_id,))
            cents = int(cur.fetchone()[0] or 0)
            return {"item_id": item_id, "cents": cents, "display": f"{cents/100:.2f}"}


def bootstrap_legacy_batches(avg_cost_cents_by_item: Optional[Dict[int,int]] = None) -> Dict:
    # Create one Legacy Batch per item with qty>0, cost from map or 0
    created = 0
    with _conn() as con:
        cur = con.cursor()
        # Prefer items.qty; if not present, try items.qty_stored/100 for backward compatibility
        # Detect columns
        cur.execute("PRAGMA table_info(items)")
        cols = {r[1] for r in cur.fetchall()}
        if "qty" in cols:
            qty_expr = "qty"
            scale = 1.0
        elif "qty_stored" in cols:
            qty_expr = "(qty_stored / 100.0)"  # best-effort fallback
            scale = 1.0
        else:
            return {"created": 0, "error": "No qty column found in items"}
        cur.execute(f"SELECT id, {qty_expr} as onhand FROM items")
        for iid, onhand in cur.fetchall():
            if (onhand or 0) <= 0: continue
            cost = (avg_cost_cents_by_item or {}).get(iid, 0)
            # create batch
            cur.execute(
                "INSERT INTO item_batches (item_id, qty_initial, qty_remaining, unit_cost_cents, source_kind, source_id) VALUES (?,?,?,?,?,?)",
                (iid, float(onhand), float(onhand), int(cost), 'legacy_migration', 'bootstrap:' + str(int(time.time())))
            )
            bid = cur.lastrowid
            # movement +
            cur.execute(
                "INSERT INTO item_movements (item_id, batch_id, qty_change, unit_cost_cents, source_kind, source_id, is_oversold) VALUES (?,?,?,?,?,?,0)",
                (iid, bid, float(onhand), int(cost), 'bootstrap', 'bootstrap:' + str(bid))
            )
            created += 1
    return {"created": created}

