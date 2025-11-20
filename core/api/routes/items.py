from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.api.app_router import ItemCreate, ItemOut, ItemUpdate, _require_vendor
from core.api.http import get_db
from core.services.models import Item

router = APIRouter()


@router.get("/items", response_model=List[ItemOut])
def list_items(
    vendor_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Item]:
    query = db.query(Item)
    if vendor_id is not None:
        query = query.filter(Item.vendor_id == vendor_id)
    return query.order_by(Item.id.desc()).all()


@router.post("/items", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    _require_vendor(db, payload.vendor_id)
    item = Item(
        vendor_id=payload.vendor_id,
        sku=payload.sku,
        name=payload.name,
        qty=payload.qty if payload.qty is not None else 0,
        unit=payload.unit,
        price=payload.price,
        notes=payload.notes,
        item_type=payload.item_type or "product",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)
) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item_not_found")
    updates = payload.dict(exclude_unset=True)
    if "vendor_id" in updates:
        _require_vendor(db, updates.get("vendor_id"))
    for field, value in updates.items():
        if field == "qty" and value is None:
            continue
        if field == "item_type" and value is None:
            continue
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item_not_found")
    db.delete(item)
    db.commit()
    return {"ok": True}


__all__ = ["router"]
