# core/api/routes/wave_sync.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os

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
    try:
        from core.wave.client import WaveClient  # lazy import
    except Exception as e:
        return {"suggestions": [], "note": f"Wave client unavailable: {e}. Install 'requests' to enable."}
    from core.wave.mapping import get_item_id

    wc = WaveClient(pat, bid)
    data = wc.query_invoices_since("1970-01-01T00:00:00Z")
    suggs: List[Suggestion] = []
    edges = (data.get('data', {}).get('business', {}) or {}).get('invoices', {}).get('edges', [])
    for e in edges:
        inv = e['node']
        for line in inv.get('items', []):
            product = line.get('product') or {}
            pid = product.get('id')
            qty = float(line.get('quantity') or 0)
            iid = get_item_id(pid) if pid else None
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
    # backend stub, no-op for now
    return {"ok": True, "applied": []}
