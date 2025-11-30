# SPDX-License-Identifier: AGPL-3.0-or-later
# core/api/routes/items.py
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.services.models import Item, Vendor
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(tags=["items"])

def _row(it: Item, vendor_name: Optional[str] = None) -> Dict[str, Any]:
    """Shape rows the way the UI expects (fields are additive/forgiving)."""
    return {
        "id": it.id,
        "name": it.name,
        "sku": it.sku,
        "qty": it.qty,
        "unit": it.unit,
        "price": it.price,
        "notes": it.notes,
        # UI reads these (optional):
        "vendor": vendor_name,          # derived from vendor_id
        "location": getattr(it, "location", None),
        "type": getattr(it, "item_type", None),  # present if column exists
        "created_at": it.created_at,
    }

@router.get("/items")
def list_items(
    req: Request,
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> List[Dict[str, Any]]:
    items = db.query(Item).all()
    vmap = {v.id: v.name for v in db.query(Vendor).all()}
    return [_row(it, vmap.get(it.vendor_id)) for it in items]

@router.get("/items/{item_id}")
def get_item(
    item_id: int,
    req: Request,
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    it = db.query(Item).get(item_id)
    if not it:
        raise HTTPException(status_code=404, detail="item not found")
    vname = None
    if it.vendor_id:
        v = db.query(Vendor).get(it.vendor_id)
        vname = v.name if v else None
    return _row(it, vname)

@router.post("/items")
def create_item(
    payload: Dict[str, Any],
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)

    location = (payload.get("location") or "").strip() or None
    item_type = payload.get("item_type") or payload.get("type")

    # Fallback upsert path used by the UI when adjusting non-existing items:
    item_id = payload.get("id")
    if item_id:
        it = db.query(Item).get(item_id)
        if it is None:
            it = Item(id=item_id)
            db.add(it)
        # Apply provided fields
        for f in ("name", "sku", "qty", "unit", "price", "notes", "vendor_id"):
            if f in payload:
                setattr(it, f, payload[f])
        if "location" in payload:
            it.location = location
        # Optional item_type if model/column exists
        if item_type is not None:
            try:
                setattr(it, "item_type", item_type)
            except Exception:
                pass
        if not getattr(it, "name", None):
            it.name = f"Item {item_id}"
    else:
        it = Item(
            name=payload.get("name") or "Unnamed Item",
            sku=payload.get("sku"),
            qty=payload.get("qty", 0),
            unit=payload.get("unit"),
            price=payload.get("price"),
            notes=payload.get("notes"),
            vendor_id=payload.get("vendor_id"),
            location=location,
        )
        if item_type is not None:
            try:
                setattr(it, "item_type", item_type)
            except Exception:
                pass
        db.add(it)

    db.commit()
    db.refresh(it)
    vname = None
    if it.vendor_id:
        v = db.query(Vendor).get(it.vendor_id)
        vname = v.name if v else None
    return _row(it, vname)

@router.put("/items/{item_id}")
def update_item(
    item_id: int,
    payload: Dict[str, Any],
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)

    it = db.query(Item).get(item_id)
    if not it:
        raise HTTPException(status_code=404, detail="item not found")

    location = (payload.get("location") or "").strip() or None
    item_type = payload.get("item_type") or payload.get("type")

    for f in ("name", "sku", "qty", "unit", "price", "notes", "vendor_id"):
        if f in payload:
            try:
                setattr(it, f, payload[f])
            except Exception:
                pass
    if "location" in payload:
        it.location = location
    if item_type is not None:
        try:
            setattr(it, "item_type", item_type)
        except Exception:
            pass

    db.commit()
    db.refresh(it)
    vname = None
    if it.vendor_id:
        v = db.query(Vendor).get(it.vendor_id)
        vname = v.name if v else None
    return _row(it, vname)

@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)

    it = db.query(Item).get(item_id)
    if not it:
        raise HTTPException(status_code=404, detail="item not found")

    db.delete(it)
    db.commit()
    return {"ok": True}
