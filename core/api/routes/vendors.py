# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Dict, List
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.services.models import Vendor

router = APIRouter(tags=["vendors"])

# Runtime token check (defers import to avoid circular refs at import time)
def _require_token_runtime(req: Request):
    from core.api.http import require_token  # runtime import
    return require_token(req)
# ---------------------------
# EXISTING /app/vendors CRUD
# ---------------------------

@router.get("/vendors")
def list_vendors(req: Request, db: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    _require_token_runtime(req)
    rows = db.query(Vendor).all()
    return [{"id": v.id, "name": v.name, "contact": getattr(v, "contact", None)} for v in rows]


@router.get("/vendors/list")
def list_vendors_compat(req: Request, db: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    return list_vendors(req, db)


@router.post("/vendors")
def create_vendor(
    req: Request,
    payload: Dict[str, Any],
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)
    require_owner_commit()

    v = Vendor(name=payload["name"], contact=payload.get("contact"))
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id, "name": v.name, "contact": getattr(v, "contact", None)}


@router.put("/vendors/{vendor_id}")
def update_vendor(
    req: Request,
    vendor_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)
    require_owner_commit()

    vendor = db.query(Vendor).get(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="vendor_not_found")

    if "name" in payload:
        vendor.name = payload["name"]
    if "contact" in payload:
        vendor.contact = payload["contact"]

    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, "name": vendor.name, "contact": getattr(vendor, "contact", None)}


@router.delete("/vendors/{vendor_id}")
def delete_vendor(
    req: Request,
    vendor_id: int,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)
    require_owner_commit()

    vendor = db.query(Vendor).get(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="vendor_not_found")
    db.delete(vendor)
    db.commit()
    return {"ok": True}


# ---------------------------
# NEW /app/contacts CRUD (same vendors table)
# ---------------------------

@router.get("/contacts")
def list_contacts(db: Session = Depends(get_session)) -> List[Dict[str, Any]]:
    rows = db.query(Vendor).all()  # default: return everything; UI can filter client-side
    out: List[Dict[str, Any]] = []
    for v in rows:
        meta: Dict[str, Any] = {}
        if getattr(v, "meta", None):
            try:
                meta = json.loads(v.meta) if isinstance(v.meta, str) else (v.meta or {})
            except Exception:
                meta = {}
        out.append({
            "id": v.id,
            "name": v.name,
            "role": getattr(v, "role", None),
            "kind": getattr(v, "kind", None),
            "organization_id": getattr(v, "organization_id", None),
            "meta": meta,
            "created_at": v.created_at,
        })
    return out


@router.post("/contacts")
def create_contact(
    req: Request,
    payload: Dict[str, Any],
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)
    require_owner_commit()

    # Desired defaults (implementation detail; SoT-agnostic)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    role_in = (payload.get("role") or "contact").strip()
    kind_in = (payload.get("kind") or "person").strip()
    organization_id = payload.get("organization_id")
    meta_in = payload.get("meta") or {}

    # Normalize incoming meta to dict
    if isinstance(meta_in, str):
        try:
            meta_in = json.loads(meta_in) if meta_in.strip() else {}
        except Exception:
            meta_in = {}

    # If a row with the same name already exists, MERGE instead of INSERT.
    existing = db.query(Vendor).filter(Vendor.name == name).first()
    if existing:
        # Upgrade role if needed
        cur_role = (existing.role or "vendor").strip() if getattr(existing, "role", None) is not None else "vendor"
        new_role = cur_role
        if {cur_role, role_in} == {"vendor", "contact"}:
            new_role = "both"
        elif cur_role == "vendor" and role_in == "vendor":
            new_role = "vendor"
        elif cur_role == "contact" and role_in == "contact":
            new_role = "contact"
        elif role_in == "both" or cur_role == "both":
            new_role = "both"

        existing.role = new_role

        # Preserve existing kind unless explicitly provided; prefer a concrete existing kind
        if "kind" in payload and kind_in:
            existing.kind = kind_in

        # organization link if the client passes one
        if organization_id is not None:
            existing.organization_id = organization_id

        # Merge meta: existing values < incoming values
        try:
            existing_meta = {}
            if getattr(existing, "meta", None):
                existing_meta = json.loads(existing.meta) if isinstance(existing.meta, str) else (existing.meta or {})
        except Exception:
            existing_meta = {}
        merged_meta = {**(existing_meta or {}), **(meta_in or {})}
        existing.meta = json.dumps(merged_meta)

        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "name": existing.name,
            "role": existing.role,
            "kind": existing.kind,
            "organization_id": existing.organization_id,
            "meta": merged_meta,
            "created_at": existing.created_at,
        }

    # No existing row — proceed to INSERT with safe fallback on IntegrityError (race).
    v = Vendor(
        name=name,
        role=role_in,
        kind=kind_in,
        organization_id=organization_id,
        meta=json.dumps(meta_in),
    )
    db.add(v)
    try:
        db.commit()
        db.refresh(v)
        return {
            "id": v.id,
            "name": v.name,
            "role": v.role,
            "kind": v.kind,
            "organization_id": v.organization_id,
            "meta": meta_in,
            "created_at": v.created_at,
        }
    except IntegrityError:
        # Another request inserted the same name concurrently: merge into that row.
        db.rollback()
        existing = db.query(Vendor).filter(Vendor.name == name).first()
        if not existing:
            # Unexpected; re-raise to surface real DB issue.
            raise
        cur_role = (existing.role or "vendor").strip() if getattr(existing, "role", None) is not None else "vendor"
        new_role = "both" if {cur_role, role_in} == {"vendor", "contact"} else (role_in if cur_role != "both" else "both")
        existing.role = new_role
        if "kind" in payload and kind_in:
            existing.kind = kind_in
        if organization_id is not None:
            existing.organization_id = organization_id
        try:
            existing_meta = {}
            if getattr(existing, "meta", None):
                existing_meta = json.loads(existing.meta) if isinstance(existing.meta, str) else (existing.meta or {})
        except Exception:
            existing_meta = {}
        merged_meta = {**(existing_meta or {}), **(meta_in or {})}
        existing.meta = json.dumps(merged_meta)
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "name": existing.name,
            "role": existing.role,
            "kind": existing.kind,
            "organization_id": existing.organization_id,
            "meta": merged_meta,
            "created_at": existing.created_at,
        }


@router.get("/contacts/{contact_id}")
def get_contact(req: Request, contact_id: int, db: Session = Depends(get_session)) -> Dict[str, Any]:
    _require_token_runtime(req)
    v = db.query(Vendor).get(contact_id)
    if not v:
        raise HTTPException(status_code=404, detail="contact not found")
    meta: Dict[str, Any] = {}
    if getattr(v, "meta", None):
        try:
            meta = json.loads(v.meta) if isinstance(v.meta, str) else (v.meta or {})
        except Exception:
            meta = {}
    return {
        "id": v.id,
        "name": v.name,
        "role": v.role,
        "kind": v.kind,
        "organization_id": v.organization_id,
        "meta": meta,
        "created_at": v.created_at,
    }


@router.put("/contacts/{contact_id}")
def update_contact(
    req: Request,
    contact_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_session),
    _w: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)

    v = db.query(Vendor).get(contact_id)
    if not v:
        raise HTTPException(status_code=404, detail="contact not found")

    if "name" in payload: v.name = payload["name"]
    if "role" in payload: v.role = payload["role"]
    if "kind" in payload: v.kind = payload["kind"]
    if "organization_id" in payload: v.organization_id = payload["organization_id"]
    if "meta" in payload:
        meta = payload["meta"]
        v.meta = json.dumps(meta) if isinstance(meta, dict) else (meta or "{}")

    db.commit()
    db.refresh(v)
    return {
        "id": v.id,
        "name": v.name,
        "role": v.role,
        "kind": v.kind,
        "organization_id": v.organization_id,
        "meta": json.loads(v.meta) if isinstance(v.meta, str) else (v.meta or {}),
        "created_at": v.created_at,
    }


@router.delete("/contacts/{contact_id}")
def delete_contact(
    req: Request,
    contact_id: int,
    db: Session = Depends(get_session),
    _w: None = Depends(require_writes),
) -> Dict[str, Any]:
    _require_token_runtime(req)

    v = db.query(Vendor).get(contact_id)
    if not v:
        raise HTTPException(status_code=404, detail="contact not found")
    db.delete(v)
    db.commit()
    return {"ok": True}
