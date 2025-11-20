from typing import Any, Dict, Generator, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.policy.guard import require_owner_commit
from core.services.models import SessionLocal, Vendor

router = APIRouter(tags=["vendors"])

# Local DB dependency (no circular import)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Runtime token check (defers import to avoid circular refs at import time)
def _require_token_runtime(req: Request):
    from core.api.http import require_token  # runtime import
    return require_token(req)


def writes_enabled():
    from core.api.http import require_writes  # runtime import
    return require_writes()

# ---------------------------
# EXISTING /app/vendors CRUD
# ---------------------------

@router.get("/vendors")
def list_vendors(req: Request, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    _require_token_runtime(req)
    rows = db.query(Vendor).all()
    return [{"id": v.id, "name": v.name, "contact": getattr(v, "contact", None)} for v in rows]


@router.get("/vendors/list")
def list_vendors_compat(req: Request, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return list_vendors(req, db)


@router.post("/vendors")
def create_vendor(req: Request, payload: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    _require_token_runtime(req)
    require_owner_commit()

    v = Vendor(name=payload["name"], contact=payload.get("contact"))
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id, "name": v.name, "contact": getattr(v, "contact", None)}


@router.put("/vendors/{vendor_id}")
def update_vendor(
    req: Request, vendor_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)
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
def delete_vendor(req: Request, vendor_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
def list_contacts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
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
    db: Session = Depends(get_db),
    _w: None = Depends(writes_enabled),
) -> Dict[str, Any]:
    _require_token_runtime(req)

    role = payload.get("role") or "contact"
    kind = payload.get("kind") or "person"
    organization_id = payload.get("organization_id")
    meta = payload.get("meta") or {}

    v = Vendor(
        name=payload["name"],
        role=role,
        kind=kind,
        organization_id=organization_id,
        meta=json.dumps(meta) if isinstance(meta, dict) else (meta or "{}"),
    )
    db.add(v)
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


@router.get("/contacts/{contact_id}")
def get_contact(req: Request, contact_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
    db: Session = Depends(get_db),
    _w: None = Depends(writes_enabled),
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
    db: Session = Depends(get_db),
    _w: None = Depends(writes_enabled),
) -> Dict[str, Any]:
    _require_token_runtime(req)

    v = db.query(Vendor).get(contact_id)
    if not v:
        raise HTTPException(status_code=404, detail="contact not found")
    db.delete(v)
    db.commit()
    return {"ok": True}
