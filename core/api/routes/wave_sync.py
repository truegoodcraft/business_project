# core/api/routes/wave_sync.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os
from core.wave.client import WaveClient
from core.wave.mapping import get_item_id
from core.ledger.service import stock_out_fifo

router = APIRouter(prefix='/app/wave', tags=['wave'])

class Suggestion(BaseModel):
    source_id: str
    item_id: int
    qty: float
    ts: str

@router.get('/suggestions')
async def suggestions():
    pat = os.environ.get('WAVE_PAT'); bid = os.environ.get('WAVE_BUSINESS_ID')
    if not pat or not bid:
        return {"suggestions": [], "note": "Set WAVE_PAT and WAVE_BUSINESS_ID env vars"}
    wc = WaveClient(pat, bid)
    data = wc.query_invoices_since("1970-01-01T00:00:00Z")
    suggs: List[Suggestion] = []
    # VERY light parsing; in real impl, handle pagination, statuses, dates
    edges = (data.get('data', {}).get('business', {}) or {}).get('invoices', {}).get('edges', [])
    for e in edges:
        inv = e['node']
        for line in inv.get('items', []):
            pid = line['product']['id'] if line.get('product') else None
            iid = get_item_id(pid) if pid else None
            qty = float(line.get('quantity') or 0)
            if iid and qty > 0:
                suggs.append({
                    'source_id': f"wave:{inv['id']}:{pid}",
                    'item_id': iid,
                    'qty': qty,
                    'ts': inv.get('createdAt')
                })
    return {"suggestions": suggs}

class ApplyPayload(BaseModel):
    ids: List[str]

@router.post('/apply')
async def apply_sales(payload: ApplyPayload):
    # For now, we expect the client to have called /suggestions and selected some entries.
    # Rebuild minimal info from ids is out of scope; caller should pass qty/item in a richer shape in the future.
    # Here we no-op to keep backend present without breaking.
    return {"ok": True, "applied": []}

