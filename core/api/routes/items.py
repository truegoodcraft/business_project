# SPDX-License-Identifier: AGPL-3.0-or-later
# core/api/routes/items.py
import math
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import asc, func
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_INVENTORY_READ, PERMISSION_INVENTORY_WRITE
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.appdb.models import CashEvent, Item, ItemBatch, ItemMovement, Vendor
from core.appdb.models_recipes import ManufacturingRun
from core.metrics.metric import UNIT_MULTIPLIER, default_unit_for, from_base
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(tags=["items"])

def _derive_qty_and_unit(uom: str, qty_stored: int) -> tuple[float, str]:
    if uom == "ea":
        return float(qty_stored), "ea"
    return qty_stored / 100.0, uom


def _cents_to_display(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _fifo_unit_cost(db: Session, item_id: int, unit_label: str) -> Tuple[Optional[int], Optional[str]]:
    batch = (
        db.query(ItemBatch)
        .filter(ItemBatch.item_id == item_id, ItemBatch.qty_remaining > 0)
        .order_by(asc(ItemBatch.created_at), asc(ItemBatch.id))
        .first()
    )
    if not batch:
        return None, None

    cents: Optional[int] = getattr(batch, "unit_cost_cents", None)
    if cents is None:
        unit_cost = getattr(batch, "unit_cost", None)
        if unit_cost is not None:
            try:
                cents = int(round(float(unit_cost) * 100))
            except Exception:
                cents = None
    if cents is None:
        total_cost_cents = getattr(batch, "total_cost_cents", None)
        qty_initial = getattr(batch, "qty_initial", None)
        if total_cost_cents is not None and qty_initial:
            try:
                cents = int(total_cost_cents) // int(qty_initial)
            except Exception:
                cents = None
    if cents is None:
        return None, None

    cents_int = int(cents)
    return cents_int, f"{_cents_to_display(cents_int)} / {unit_label}"


def _reject_quantity_mutation(payload: Dict[str, Any]) -> None:
    if "qty" in payload or "qty_stored" in payload:
        raise HTTPException(status_code=400, detail="inventory_quantity_requires_stock_movement")


def _validated_item_price(payload: Dict[str, Any]) -> tuple[bool, float | None]:
    if "price_decimal" in payload:
        raw_value = payload.get("price_decimal")
    elif "price" in payload:
        raw_value = payload.get("price")
    else:
        return False, None

    # Preserve the existing optional-price contract. An empty UI product price
    # means zero, while a null metadata field means no price update.
    if raw_value is None:
        return True, None
    if isinstance(raw_value, str) and not raw_value.strip():
        raw_value = "0"
    try:
        decimal_value = Decimal(str(raw_value).strip())
        float_value = float(decimal_value)
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=400, detail="item_price_invalid") from exc
    if not decimal_value.is_finite() or decimal_value < 0 or not math.isfinite(float_value):
        raise HTTPException(status_code=400, detail="item_price_invalid")
    return True, float_value

def _items_with_onhand(db: Session):
    onhand_sq = (
        db.query(
            ItemBatch.item_id.label("item_id"),
            func.coalesce(func.sum(ItemBatch.qty_remaining), 0).label("on_hand"),
        )
        .filter(ItemBatch.qty_remaining > 0)
        .group_by(ItemBatch.item_id)
        .subquery()
    )
    return (
        db.query(Item, func.coalesce(onhand_sq.c.on_hand, 0).label("on_hand"))
        .outerjoin(onhand_sq, onhand_sq.c.item_id == Item.id)
    )


def _on_hand_fields(it: Item, on_hand: int) -> Dict[str, Any]:
    dimension = it.dimension if getattr(it, "dimension", None) in UNIT_MULTIPLIER else "count"
    unit = (getattr(it, "uom", None) or default_unit_for(dimension)).lower()
    if unit not in UNIT_MULTIPLIER.get(dimension, {}):
        unit = default_unit_for(dimension)
    try:
        display_qty = from_base(int(on_hand), unit, dimension)
    except Exception:
        dimension = "count"
        unit = default_unit_for(dimension)
        display_qty = from_base(int(on_hand), unit, dimension)
    return {
        "stock_on_hand_int": int(on_hand),
        "stock_on_hand_display": {"unit": unit, "value": str(display_qty)},
    }


def _row(it: Item, vendor_name: Optional[str] = None, on_hand: Optional[int] = None) -> Dict[str, Any]:
    """Shape rows the way the UI expects (fields are additive/forgiving)."""
    qty_stored = int(getattr(it, "qty_stored", 0) or 0)
    uom = getattr(it, "uom", "ea") or "ea"
    qty, unit = _derive_qty_and_unit(uom, qty_stored)
    row = {
        "id": it.id,
        "name": it.name,
        "sku": it.sku,
        "dimension": getattr(it, "dimension", None),
        "uom": uom,
        "qty_stored": qty_stored,
        "qty": qty,
        "unit": unit,
        "price": it.price,
        "is_product": bool(getattr(it, "is_product", False)),
        "notes": it.notes,
        # UI reads these (optional):
        "vendor_id": int(it.vendor_id) if getattr(it, "vendor_id", None) is not None else None,
        "vendor": vendor_name,          # derived from vendor_id
        "location": getattr(it, "location", None),
        "type": getattr(it, "item_type", None),  # present if column exists
        "created_at": it.created_at,
    }
    if on_hand is not None:
        row.update(_on_hand_fields(it, on_hand))
    else:
        row.setdefault("stock_on_hand_int", 0)
        row.setdefault(
            "stock_on_hand_display",
            {"unit": default_unit_for(getattr(it, "dimension", "count") or "count"), "value": "0.000"},
        )
    row.setdefault("fifo_unit_cost_cents", None)
    row.setdefault("fifo_unit_cost_display", None)
    return row

@router.get("/items")
def list_items(
    include_archived: bool = Query(False),
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_INVENTORY_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> List[Dict[str, Any]]:
    items_query = _items_with_onhand(db)
    if not include_archived:
        items_query = items_query.filter(Item.is_archived == False)
    items = items_query.all()
    vmap = {v.id: v.name for v in db.query(Vendor).all()}
    rows: List[Dict[str, Any]] = []
    for it, on_hand in items:
        row = _row(it, vmap.get(it.vendor_id), on_hand)
        display_unit = row.get("stock_on_hand_display", {}).get("unit") or default_unit_for(
            getattr(it, "dimension", "count") or "count"
        )
        fifo_cents, fifo_display = _fifo_unit_cost(db, it.id, display_unit)
        row["fifo_unit_cost_cents"] = fifo_cents
        row["fifo_unit_cost_display"] = fifo_display
        rows.append(row)
    return rows

@router.get("/items/{item_id}")
def get_item(
    item_id: int,
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_INVENTORY_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    row = _items_with_onhand(db).filter(Item.id == item_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="item not found")
    it, on_hand = row
    vname = None
    if it.vendor_id:
        v = db.query(Vendor).get(it.vendor_id)
        vname = v.name if v else None

    base_row = _row(it, vname, on_hand)
    display_unit = base_row.get("stock_on_hand_display", {}).get("unit") or default_unit_for(
        getattr(it, "dimension", "count") or "count"
    )
    fifo_cents, fifo_display = _fifo_unit_cost(db, it.id, display_unit)
    base_row["fifo_unit_cost_cents"] = fifo_cents
    base_row["fifo_unit_cost_display"] = fifo_display

    batches = (
        db.query(ItemBatch)
        .filter(ItemBatch.item_id == item_id)
        .order_by(asc(ItemBatch.created_at), asc(ItemBatch.id))
        .all()
    )
    summary: List[Dict[str, Any]] = []
    for b in batches:
        unit_cost_cents = getattr(b, "unit_cost_cents", None)
        if unit_cost_cents is None:
            unit_cost = getattr(b, "unit_cost", None)
            if unit_cost is not None:
                try:
                    unit_cost_cents = int(round(float(unit_cost) * 100))
                except Exception:
                    unit_cost_cents = None
        if unit_cost_cents is None:
            unit_cost_cents = 0
        summary.append(
            {
                "entered": b.created_at.isoformat() if getattr(b, "created_at", None) else "",
                "remaining_int": int(getattr(b, "qty_remaining", 0) or 0),
                "original_int": int(getattr(b, "qty_initial", getattr(b, "qty_remaining", 0)) or 0),
                "unit_cost_display": f"{_cents_to_display(int(unit_cost_cents))} / {display_unit}",
            }
        )

    base_row["batches_summary"] = summary
    return base_row

@router.post("/items")
def create_item(
    req: Request,
    resp: Response,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVENTORY_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)
    _reject_quantity_mutation(payload)

    location = (payload.get("location") or "").strip() or None
    item_type = payload.get("item_type") or payload.get("type")
    dimension = (payload.get("dimension") or "count").lower()
    uom = (payload.get("uom") or payload.get("unit") or default_unit_for(dimension)).lower()
    if dimension not in UNIT_MULTIPLIER:
        raise HTTPException(status_code=400, detail="unsupported dimension")
    if uom not in UNIT_MULTIPLIER.get(dimension, {}):
        raise HTTPException(status_code=400, detail="unsupported uom")
    is_product = bool(payload.get("is_product"))
    price_provided, price_val = _validated_item_price(payload)

    # Fallback upsert path used by the UI when adjusting non-existing items:
    item_id = payload.get("id")
    if item_id:
        it = db.query(Item).get(item_id)
        if it is None:
            it = Item(id=item_id)
            db.add(it)
        # Apply provided fields
        for f in ("name", "sku", "notes", "vendor_id"):
            if f in payload:
                setattr(it, f, payload[f])
        if price_provided or is_product:
            if price_val is not None:
                it.price = price_val
            elif is_product:
                it.price = 0
        it.dimension = dimension
        it.uom = uom
        it.is_product = is_product
        if "location" in payload:
            it.location = location
        # Optional item_type if model/column exists
        if item_type is not None:
            try:
                setattr(it, "item_type", item_type)
            except AttributeError:  # Compatibility fallback: older Item models may not expose item_type.
                pass
        if not getattr(it, "name", None):
            it.name = f"Item {item_id}"
        if it.id is None or getattr(it, "qty_stored", None) is None:
            it.qty_stored = 0
    else:
        it = Item(
            name=payload.get("name") or "Unnamed Item",
            sku=payload.get("sku"),
            price=price_val if price_val is not None else (0 if is_product else None),
            notes=payload.get("notes"),
            vendor_id=payload.get("vendor_id"),
            location=location,
            dimension=dimension,
            uom=uom,
            qty_stored=0,
            is_product=is_product,
        )
        if item_type is not None:
            try:
                setattr(it, "item_type", item_type)
            except AttributeError:  # Compatibility fallback: older Item models may not expose item_type.
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
    req: Request,
    resp: Response,
    item_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVENTORY_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)
    _reject_quantity_mutation(payload)

    it = db.query(Item).get(item_id)
    if not it:
        raise HTTPException(status_code=404, detail="item not found")

    location = (payload.get("location") or "").strip() or None
    item_type = payload.get("item_type") or payload.get("type")
    dimension = (payload.get("dimension") or getattr(it, "dimension", "count") or "count").lower()
    uom = (payload.get("uom") or payload.get("unit") or getattr(it, "uom", None) or default_unit_for(dimension)).lower()
    if dimension not in UNIT_MULTIPLIER:
        raise HTTPException(status_code=400, detail="unsupported dimension")
    if uom not in UNIT_MULTIPLIER.get(dimension, {}):
        raise HTTPException(status_code=400, detail="unsupported uom")
    price_provided, price_val = _validated_item_price(payload)

    for f in ("name", "sku", "notes", "vendor_id"):
        if f in payload:
            setattr(it, f, payload[f])
    if price_provided or ("is_product" in payload):
        if price_val is not None:
            it.price = price_val
        elif payload.get("is_product"):
            it.price = 0
    if "is_product" in payload:
        it.is_product = bool(payload.get("is_product"))
    it.dimension = dimension
    it.uom = uom
    if "location" in payload:
        it.location = location
    if item_type is not None:
        try:
            setattr(it, "item_type", item_type)
        except AttributeError:  # Compatibility fallback: older Item models may not expose item_type.
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
    req: Request,
    item_id: int,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVENTORY_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
) -> Dict[str, Any]:
    require_owner_commit(req)

    it = db.query(Item).get(item_id)
    if not it:
        raise HTTPException(status_code=404, detail="item not found")

    has_item_movement = db.query(ItemMovement.id).filter(ItemMovement.item_id == item_id).first() is not None
    has_cash_event = db.query(CashEvent.id).filter(CashEvent.item_id == item_id).first() is not None
    has_manufacturing_run = (
        db.query(ManufacturingRun.id).filter(ManufacturingRun.output_item_id == item_id).first() is not None
    )
    if has_item_movement or has_cash_event or has_manufacturing_run:
        it.is_archived = True
        db.commit()
        return {"archived": True}

    # Remove dependent batches to avoid orphaned rows if SQLite reuses item ids after delete
    db.query(ItemBatch).filter(ItemBatch.item_id == item_id).delete(synchronize_session=False)
    db.delete(it)
    db.commit()
    return {"ok": True}
