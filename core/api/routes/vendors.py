from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.api.http import get_db
from core.api.http import require_session_token as require_session
from core.api.app_router import ContactOut, VendorCreate, VendorOut, VendorUpdate
from core.services.models import Vendor

router = APIRouter()


@router.get("/vendors", response_model=List[VendorOut])
def list_vendors(db: Session = Depends(get_db)) -> List[Vendor]:
    return db.query(Vendor).order_by(Vendor.id.desc()).all()


@router.post("/vendors", response_model=VendorOut)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)) -> Vendor:
    vendor = Vendor(**payload.dict())
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
    vendor_id: int, payload: VendorUpdate, db: Session = Depends(get_db)
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
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)) -> dict:
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status_code=404, detail="vendor_not_found")
    db.delete(vendor)
    db.commit()
    return {"ok": True}


@router.get("/app/vendors")
def get_vendors(
    db: Session = Depends(get_db),
    token: str = Depends(require_session),
):
    rows = db.query(Vendor).all()
    return [{"id": r.id, "name": r.name} for r in rows]


@router.post("/app/vendors")
def create_app_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    token: str = Depends(require_session),
):
    vendor = Vendor(name=payload.name, contact=payload.contact)
    db.add(vendor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="vendor_name_conflict") from exc
    db.refresh(vendor)
    return {"id": vendor.id, "name": vendor.name}


ALLOWED_ROLES = {"vendor", "contact", "both"}
ALLOWED_KINDS = {"org", "person"}


def _coerce_meta(meta: Optional[Any]) -> Optional[str]:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return json.dumps(meta)
    if isinstance(meta, str):
        return meta
    return json.dumps(meta)


def _parse_meta(meta: Optional[str]) -> Optional[Dict[str, Any]]:
    if meta is None or meta == "":
        return None
    try:
        return json.loads(meta)
    except (TypeError, ValueError):
        return None


@router.get("/contacts", response_model=List[ContactOut])
def list_contacts(db: Session = Depends(get_db)) -> List[Vendor]:
    rows = db.query(Vendor).order_by(Vendor.id.desc()).all()
    for row in rows:
        row.meta = _parse_meta(row.meta) if hasattr(row, "meta") else None
    return rows


@router.get("/contacts/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)) -> Vendor:
    contact = db.get(Vendor, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="contact_not_found")
    if hasattr(contact, "meta"):
        contact.meta = _parse_meta(contact.meta)
    return contact


class ContactCreate(VendorCreate):
    role: Optional[str] = None
    kind: Optional[str] = None
    organization_id: Optional[int] = None
    meta: Optional[Any] = None


class ContactUpdate(VendorUpdate):
    role: Optional[str] = None
    kind: Optional[str] = None
    organization_id: Optional[int] = None
    meta: Optional[Any] = None


@router.post("/contacts", response_model=ContactOut)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)) -> Vendor:
    role = payload.role or "contact"
    kind = payload.kind or "person"
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="invalid_role")
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="invalid_kind")
    contact = Vendor(
        name=payload.name,
        contact=payload.contact,
        role=role,
        kind=kind,
        organization_id=payload.organization_id,
        meta=_coerce_meta(payload.meta),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    contact.meta = _parse_meta(contact.meta)
    return contact


@router.put("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int, payload: ContactUpdate, db: Session = Depends(get_db)
) -> Vendor:
    contact = db.get(Vendor, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="contact_not_found")
    updates = payload.dict(exclude_unset=True)
    if "role" in updates:
        role = updates["role"] or "contact"
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="invalid_role")
        updates["role"] = role
    if "kind" in updates:
        kind = updates["kind"] or "person"
        if kind not in ALLOWED_KINDS:
            raise HTTPException(status_code=400, detail="invalid_kind")
        updates["kind"] = kind
    if "meta" in updates:
        updates["meta"] = _coerce_meta(updates.get("meta"))
    for field, value in updates.items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    contact.meta = _parse_meta(contact.meta)
    return contact


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)) -> dict:
    contact = db.get(Vendor, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="contact_not_found")
    db.delete(contact)
    db.commit()
    return {"ok": True}


__all__ = ["router"]
