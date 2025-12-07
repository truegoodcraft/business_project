# SPDX-License-Identifier: AGPL-3.0-or-later
# core/api/routes/items.py
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.services.models import Item, Vendor
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(tags=["items"])

UOMS = {"ea", "g", "mm", "mm2", "mm3"}
MAX_INT64 = 2**63 - 1


def _derive_qty_and_unit(uom: str, qty_stored: int) -> tuple[float, str]:
    if uom == "ea":
        return float(qty_stored), "ea"
    return qty_stored / 100.0, uom


def _round_half_away_from_zero(val: float) -> int:
    sign = -1 if val < 0 else 1
    return int((abs(val) + 0.5) // 1 * sign)


def _guard_int_bounds(value: int):
    if abs(int(value)) > MAX_INT64:
        raise HTTPException(status_code=400, detail="quantity overflow: exceeds 64-bit integer")


def _to_stored(qty: float, uom: str) -> int:
    if uom == "ea":
        stored = _round_half_away_from_zero(qty)
    else:
        stored = _round_half_away_from_zero(qty * 100)
    _guard_int_bounds(stored)
    return stored


def _apply_qty_fields(it: Item, payload: Dict[str, Any], resp: Optional[Response] = None):
    uom = (payload.get("uom") or payload.get("unit") or getattr(it, "uom", "ea") or "ea").lower()
    if uom not in UOMS:
        raise HTTPException(status_code=400, detail="unsupported uom")
    qty_stored = payload.get("qty_stored")
    used_legacy = False
    if qty_stored is None:
        if "qty" in payload:
            qty_val = payload.get("qty") or 0
            qty_stored = _to_stored(float(qty_val), uom)
            used_legacy = True
        else:
            qty_stored = getattr(it, "qty_stored", 0) or 0
    else:
        try:
            qty_stored = int(qty_stored)
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail="qty_stored must be integer") from exc
        _guard_int_bounds(qty_stored)

    it.uom = uom
    it.qty_stored = qty_stored
    if used_legacy and resp is not None:
        resp.headers["X-BUS-Deprecation"] = "qty/unit"

def _row(it: Item, vendor_name: Optional[str] = None) -> Dict[str, Any]:
    """Shape rows the way the UI expects (fields are additive/forgiving)."""
    qty_stored = int(getattr(it, "qty_stored", 0) or 0)
    uom = getattr(it, "uom", "ea") or "ea"
    qty, unit = _derive_qty_and_unit(uom, qty_stored)
    return {
        "id": it.id,
        "name": it.name,
        "sku": it.sku,
        "uom": uom,
        "qty_stored": qty_stored,
        "qty": qty,
        "unit": unit,
        "price": it.price,
        "notes": it.notes,
        # ADDED: Essential for UI binding and testing
        "vendor_id": it.vendor_id,
        # UI reads these (optional):
        "vendor": vendor_name,          # derived from vendor_id
        "location": getattr(it, "location", None),
        "type": getattr(it, "item_type", None),  # present if column exists
        "created_at": it.created_at,
    }

@router.get("/items")
def list_items(
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
    req: Request,
    resp: Response,
    payload: Dict[str, Any] = Body(...),
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
        for f in ("name", "sku", "price", "notes", "vendor_id"):
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
        _apply_qty_fields(it, payload, resp)
    else:
        it = Item(
            name=payload.get("name") or "Unnamed Item",
            sku=payload.get("sku"),
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
        _apply_qty_fields(it, payload, resp)
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
    req: Request,
    resp: Response,
    item_id: int,
    payload: Dict[str, Any] = Body(...),
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

    for f in ("name", "sku", "price", "notes", "vendor_id"):
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

    _apply_qty_fields(it, payload, resp)
    db.commit()
    db.refresh(it)
    vname = None
    if it.vendor_id:
        v = db.query(Vendor).get(it.vendor_id)
        vname = v.name if v else None
    return _row(it, vname)

@router.delete("/items/{item_id}")
def delete_item(
    req: Request,
    item_id: int,
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
