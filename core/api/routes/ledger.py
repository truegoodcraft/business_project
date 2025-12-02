# core/api/routes/ledger.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.ledger.service import stock_in, stock_out_fifo, valuation, bootstrap_legacy_batches
from core.ledger.health import health_summary

router = APIRouter(prefix='/app', tags=['ledger'])

class Adjustment(BaseModel):
    item_id: int
    delta: float
    unit_cost_cents: int = 0
    source_id: Optional[str] = None

@router.get('/ledger/movements')
async def list_movements(item_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    import sqlite3, os
    con = sqlite3.connect(os.environ.get('BUS_DB', 'data/app.db'))
    cur = con.cursor()
    if item_id is None:
        cur.execute("SELECT id,item_id,batch_id,qty_change,unit_cost_cents,source_kind,source_id,is_oversold,created_at FROM item_movements ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
    else:
        cur.execute("SELECT id,item_id,batch_id,qty_change,unit_cost_cents,source_kind,source_id,is_oversold,created_at FROM item_movements WHERE item_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (item_id, limit, offset))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

@router.get('/ledger/batches')
async def list_batches(item_id: Optional[int] = None, only_open: bool = True):
    import sqlite3, os
    con = sqlite3.connect(os.environ.get('BUS_DB', 'data/app.db'))
    cur = con.cursor()
    base = "SELECT id,item_id,qty_initial,qty_remaining,unit_cost_cents,source_kind,source_id,created_at FROM item_batches"
    where = []
    params = []
    if item_id is not None:
        where.append("item_id=?"); params.append(item_id)
    if only_open:
        where.append("qty_remaining > 0")
    if where:
        base += " WHERE " + " AND ".join(where)
    base += " ORDER BY item_id, created_at"
    cur.execute(base, tuple(params))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

@router.get('/valuation')
async def get_valuation(item_id: Optional[int] = None):
    return valuation(item_id)

@router.get('/ledger/health')
async def get_health():
    return health_summary()

@router.post('/ledger/adjustments')
async def post_adjustment(adj: Adjustment):
    if adj.delta == 0:
        return {"ok": True}
    sid = adj.source_id or f"manual:{adj.item_id}:{adj.delta}"
    if adj.delta > 0:
        res = stock_in(adj.item_id, adj.delta, adj.unit_cost_cents, 'adjustment', sid)
    else:
        res = stock_out_fifo(adj.item_id, -adj.delta, 'adjustment', sid)
    return {"ok": True, "result": res.__dict__}

@router.post('/ledger/bootstrap')
async def post_bootstrap():
    return bootstrap_legacy_batches()

