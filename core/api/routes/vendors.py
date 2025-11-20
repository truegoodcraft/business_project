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
def create_contact(contact_in: ContactCreate, db: Session = Depends(get_db)):
    # Coerce defaults if omitted/missing
    desired_role = getattr(contact_in, "role", None) or "contact"
    desired_kind = getattr(contact_in, "kind", None) or "person"

    # Normalize meta inbound -> TEXT (JSON-encoded)
    inbound_meta = getattr(contact_in, "meta", None)
    if isinstance(inbound_meta, dict):
        meta_text = json.dumps(inbound_meta)
    elif isinstance(inbound_meta, str):
        try:
            # accept JSON string; if not JSON, store as wrapper
            json.loads(inbound_meta)
            meta_text = inbound_meta
        except Exception:
            meta_text = json.dumps({"_raw": inbound_meta})
    else:
        meta_text = None

    v = Vendor(
        name=contact_in.name,
        contact=getattr(contact_in, "contact", None),
        role=desired_role,
        kind=desired_kind,
        organization_id=getattr(contact_in, "organization_id", None),
        meta=meta_text,
    )

    db.add(v)
    try:
        db.commit()
        db.refresh(v)
        row = v
    except IntegrityError:
        # UNIQUE(vendors.name) collision -> merge/upgrade existing row
        db.rollback()
        existing = db.query(Vendor).filter(Vendor.name == contact_in.name).first()
        if not existing:
            # Not a name-collision; bubble up
            raise

        # Upgrade role if needed
        current_role = existing.role or "vendor"
        if {current_role, desired_role} == {"vendor", "contact"}:
            existing.role = "both"

        # Only override kind if client explicitly sent it
        if getattr(contact_in, "kind", None):
            existing.kind = desired_kind

        # Merge meta (incoming wins)
        if inbound_meta is not None:
            try:
                existing_meta_obj = json.loads(existing.meta) if existing.meta else {}
                if not isinstance(existing_meta_obj, dict):
                    existing_meta_obj = {}
            except Exception:
                existing_meta_obj = {}

            if isinstance(inbound_meta, str):
                try:
                    inbound_meta_obj = json.loads(inbound_meta) if inbound_meta else {}
                except Exception:
                    inbound_meta_obj = {"_raw": inbound_meta}
            else:
                inbound_meta_obj = inbound_meta or {}

            existing_meta_obj.update(inbound_meta_obj)
            existing.meta = json.dumps(existing_meta_obj)

        db.add(existing)
        db.commit()
        db.refresh(existing)
        row = existing

    # Prepare response as a plain dict (UI expects dict here, not strict Pydantic)
    try:
        meta_obj = json.loads(row.meta) if row.meta else None
    except Exception:
        meta_obj = {"_raw": row.meta} if row.meta else None

    return {
        "id": row.id,
        "name": row.name,
        "contact": getattr(row, "contact", None),
        "role": row.role,
        "kind": row.kind,
        "organization_id": row.organization_id,
        "meta": meta_obj,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


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
