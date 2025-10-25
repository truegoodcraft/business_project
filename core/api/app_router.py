"""FastAPI router for domain CRUD backed by SQLAlchemy."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.services.models import Attachment, Item, Task, Vendor, get_session

router = APIRouter(tags=["app"])


# ---- Pydantic models -----------------------------------------------------


class VendorBase(BaseModel):
    name: str
    contact: Optional[str] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    notes: Optional[str] = None


class VendorOut(VendorBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class ItemBase(BaseModel):
    vendor_id: Optional[int] = None
    sku: Optional[str] = None
    name: str
    qty: Optional[float] = 0
    unit: Optional[str] = None
    price: Optional[float] = None
    notes: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    vendor_id: Optional[int] = None
    sku: Optional[str] = None
    name: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    notes: Optional[str] = None


class ItemOut(ItemBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class TaskBase(BaseModel):
    item_id: Optional[int] = None
    title: str
    status: Optional[str] = "pending"
    due: Optional[date] = None
    notes: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    item_id: Optional[int] = None
    title: Optional[str] = None
    status: Optional[str] = None
    due: Optional[date] = None
    notes: Optional[str] = None


class TaskOut(TaskBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class AttachmentBase(BaseModel):
    reader_id: str
    label: Optional[str] = None


class AttachmentOut(AttachmentBase):
    id: int
    entity_type: str
    entity_id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---- Helpers -------------------------------------------------------------


def _require_vendor(db: Session, vendor_id: Optional[int]) -> None:
    if vendor_id is None:
        return
    if db.get(Vendor, vendor_id) is None:
        raise HTTPException(status_code=422, detail="vendor_not_found")


def _require_item(db: Session, item_id: Optional[int]) -> None:
    if item_id is None:
        return
    if db.get(Item, item_id) is None:
        raise HTTPException(status_code=422, detail="item_not_found")


def _require_entity(db: Session, entity_type: str, entity_id: int) -> None:
    mapping = {
        "vendor": Vendor,
        "item": Item,
        "task": Task,
    }
    model = mapping.get(entity_type)
    if model is None:
        raise HTTPException(status_code=400, detail="unsupported_entity_type")
    if db.get(model, entity_id) is None:
        raise HTTPException(status_code=404, detail="entity_not_found")


# ---- Vendor endpoints ----------------------------------------------------


@router.get("/vendors", response_model=List[VendorOut])
def list_vendors(db: Session = Depends(get_session)) -> List[Vendor]:
    return db.query(Vendor).order_by(Vendor.id.desc()).all()


@router.post("/vendors", response_model=VendorOut)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_session)) -> Vendor:
    vendor = Vendor(name=payload.name, contact=payload.contact, notes=payload.notes)
    db.add(vendor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="vendor_name_conflict") from exc
    db.refresh(vendor)
    return vendor


@router.put("/vendors/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: int, payload: VendorUpdate, db: Session = Depends(get_session)
) -> Vendor:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="vendor_not_found")
    updates = payload.dict(exclude_unset=True)
    for field, value in updates.items():
        setattr(vendor, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="vendor_name_conflict") from exc
    db.refresh(vendor)
    return vendor


@router.delete("/vendors/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_session)) -> dict:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="vendor_not_found")
    db.delete(vendor)
    db.commit()
    return {"ok": True}


# ---- Item endpoints ------------------------------------------------------


@router.get("/items", response_model=List[ItemOut])
def list_items(
    vendor_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_session),
) -> List[Item]:
    query = db.query(Item)
    if vendor_id is not None:
        query = query.filter(Item.vendor_id == vendor_id)
    return query.order_by(Item.id.desc()).all()


@router.post("/items", response_model=ItemOut)
def create_item(payload: ItemCreate, db: Session = Depends(get_session)) -> Item:
    _require_vendor(db, payload.vendor_id)
    item = Item(
        vendor_id=payload.vendor_id,
        sku=payload.sku,
        name=payload.name,
        qty=payload.qty if payload.qty is not None else 0,
        unit=payload.unit,
        price=payload.price,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int, payload: ItemUpdate, db: Session = Depends(get_session)
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
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_session)) -> dict:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item_not_found")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ---- Task endpoints ------------------------------------------------------


@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(
    item_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_session),
) -> List[Task]:
    query = db.query(Task)
    if item_id is not None:
        query = query.filter(Task.item_id == item_id)
    return query.order_by(Task.id.desc()).all()


@router.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_session)) -> Task:
    _require_item(db, payload.item_id)
    task = Task(
        item_id=payload.item_id,
        title=payload.title,
        status=payload.status or "pending",
        due=payload.due,
        notes=payload.notes,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: Session = Depends(get_session)
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    updates = payload.dict(exclude_unset=True)
    if "item_id" in updates:
        _require_item(db, updates.get("item_id"))
    for field, value in updates.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_session)) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task_not_found")
    db.delete(task)
    db.commit()
    return {"ok": True}


# ---- Attachment endpoints ------------------------------------------------


@router.get(
    "/attachments/{entity_type}/{entity_id}", response_model=List[AttachmentOut]
)
def list_attachments(
    entity_type: str, entity_id: int, db: Session = Depends(get_session)
) -> List[Attachment]:
    _require_entity(db, entity_type, entity_id)
    return (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .order_by(Attachment.id.desc())
        .all()
    )


@router.post(
    "/attachments/{entity_type}/{entity_id}", response_model=AttachmentOut
)
def create_attachment(
    entity_type: str,
    entity_id: int,
    payload: AttachmentBase,
    db: Session = Depends(get_session),
) -> Attachment:
    _require_entity(db, entity_type, entity_id)
    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        reader_id=payload.reader_id,
        label=payload.label,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_session)) -> dict:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="attachment_not_found")
    db.delete(attachment)
    db.commit()
    return {"ok": True}


__all__ = ["router"]
