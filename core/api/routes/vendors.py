# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.appdb.models import Vendor as VendorModel
from core.appdb.session import get_db
from core.api.schemas.vendors import VendorCreate, VendorOut, VendorUpdate
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx

router = APIRouter(tags=["vendors"])


def _apply_defaults_for_facade(payload: dict, facade: str) -> dict:
    # Only set defaults if missing
    if facade == "contacts":
        payload.setdefault("role", "contact")
        payload.setdefault("kind", "person")
    else:
        payload.setdefault("role", "vendor")
        payload.setdefault("kind", "org")
    return payload


def _query_filters(q: Optional[str], role: Optional[str], kind: Optional[str], organization_id: Optional[int]):
    filters = []
    if q:
        like = f"%{q}%"
        filters.append(or_(VendorModel.name.ilike(like), VendorModel.contact.ilike(like)))
    if role and role.lower() != "any":
        filters.append(VendorModel.role == role.lower())
    if kind:
        filters.append(VendorModel.kind == kind.lower())
    if organization_id is not None:
        filters.append(VendorModel.organization_id == organization_id)
    return filters


def _normalize_role_kind(data: dict) -> dict:
    for key in ("role", "kind"):
        if key in data and isinstance(data[key], str):
            data[key] = data[key].lower()
    return data


def _crud_routes(prefix: str, facade: str):
    @router.get(prefix, response_model=List[VendorOut])
    def list_vendors(
        q: Optional[str] = None,
        role: Optional[str] = Query(None, description="vendor|contact|both|any"),
        kind: Optional[str] = Query(None, description="org|person"),
        organization_id: Optional[int] = Query(None, description="Filter by parent org ID"),
        db: Session = Depends(get_db),
        _token: str = Depends(require_token_ctx),
    ):
        query = db.query(VendorModel)
        for f in _query_filters(q, role, kind, organization_id):
            query = query.filter(f)
        return query.order_by(VendorModel.name.asc()).all()

    @router.get(f"{prefix}" + "/{id}", response_model=VendorOut)
    def get_vendor(id: int, db: Session = Depends(get_db), _token: str = Depends(require_token_ctx)):
        v = db.query(VendorModel).get(id)
        if not v:
            raise HTTPException(status_code=404, detail="Not found")
        return v

    @router.post(prefix, response_model=VendorOut, status_code=201)
    def create_vendor(
        payload: VendorCreate,
        db: Session = Depends(get_db),
        _writes: None = Depends(require_writes),
        _token: str = Depends(require_token_ctx),
    ):
        require_owner_commit()
        data = _apply_defaults_for_facade(payload.model_dump(exclude_unset=True), facade)
        data = _normalize_role_kind(data)
        v = VendorModel(**data)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v

    @router.put(f"{prefix}" + "/{id}", response_model=VendorOut)
    def update_vendor(
        id: int,
        payload: VendorUpdate,
        db: Session = Depends(get_db),
        _writes: None = Depends(require_writes),
        _token: str = Depends(require_token_ctx),
    ):
        require_owner_commit()
        v = db.query(VendorModel).get(id)
        if not v:
            raise HTTPException(status_code=404, detail="Not found")
        updates = _normalize_role_kind(payload.model_dump(exclude_unset=True))
        for k, val in updates.items():
            setattr(v, k, val)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v

    @router.delete(f"{prefix}" + "/{id}", status_code=204)
    def delete_vendor(
        id: int,
        cascade_children: bool = Query(False),
        db: Session = Depends(get_db),
        _writes: None = Depends(require_writes),
        _token: str = Depends(require_token_ctx),
    ):
        require_owner_commit()
        v = db.query(VendorModel).get(id)
        if not v:
            raise HTTPException(status_code=404, detail="Not found")

        # If org with dependents: either cascade delete or auto-null children
        if v.kind == "org":
            children = db.query(VendorModel).filter(VendorModel.organization_id == id)
            if cascade_children:
                children.delete(synchronize_session=False)
            else:
                children.update({"organization_id": None}, synchronize_session=False)

        db.delete(v)
        db.commit()
        return


# Mount façade routes
_crud_routes("/app/vendors", "vendors")
_crud_routes("/app/contacts", "contacts")
