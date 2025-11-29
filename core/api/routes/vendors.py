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


def _apply_defaults(payload: dict, facade: str, existing: Optional[VendorModel] = None) -> dict:
    data = payload.copy()
    data.pop("kind", None)
    if "is_vendor" in data and data["is_vendor"] is not None:
        data["is_vendor"] = 1 if bool(data["is_vendor"]) else 0
        data["role"] = "vendor" if data["is_vendor"] else "contact"
    elif "role" in data and data["role"] is not None:
        is_vendor = str(data["role"]).lower() in ("vendor", "both")
        data["is_vendor"] = 1 if is_vendor else 0
        data["role"] = "vendor" if is_vendor else "contact"
    else:
        if existing is not None:
            data.setdefault("is_vendor", existing.is_vendor)
            data.setdefault("role", existing.role)
        else:
            default_vendor = 1 if facade == "vendors" else 0
            data.setdefault("is_vendor", default_vendor)
            data.setdefault("role", "vendor" if default_vendor else "contact")
    data["role"] = str(data.get("role", "contact")).lower()
    if existing is not None:
        data.setdefault("is_org", existing.is_org)
    data["is_org"] = 1 if bool(data.get("is_org")) else 0
    return data


def _query_filters(q: Optional[str], role: Optional[str], organization_id: Optional[int], role_in: Optional[str], is_vendor: Optional[bool], is_org: Optional[bool]):
    filters = []
    if q:
        like = f"%{q}%"
        filters.append(or_(VendorModel.name.ilike(like), VendorModel.contact.ilike(like)))
    if role and role.lower() != "any":
        filters.append(VendorModel.role == role.lower())
    if organization_id is not None:
        filters.append(VendorModel.organization_id == organization_id)
    if is_vendor is not None:
        filters.append(VendorModel.is_vendor == (1 if str(is_vendor).lower() == "true" else 0))
    if is_org is not None:
        filters.append(VendorModel.is_org == (1 if str(is_org).lower() == "true" else 0))
    if role_in:
        roles = [r.strip().lower() for r in role_in.split(",") if r.strip()]
        if roles:
            filters.append(VendorModel.role.in_(roles))
    return filters


def _crud_routes(prefix: str, facade: str):
    @router.get(prefix, response_model=List[VendorOut])
    def list_vendors(
        q: Optional[str] = None,
        role: Optional[str] = Query(None, description="vendor|contact|both|any"),
        role_in: Optional[str] = Query(None, description="CSV of roles (compat)"),
        is_vendor: Optional[bool] = Query(None, description="Filter by vendor flag"),
        is_org: Optional[bool] = Query(None, description="Filter by organization flag"),
        organization_id: Optional[int] = Query(None, description="Filter by parent org ID"),
        db: Session = Depends(get_db),
        _token: str = Depends(require_token_ctx),
    ):
        query = db.query(VendorModel)
        for f in _query_filters(q, role, organization_id, role_in, is_vendor, is_org):
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
        data = _apply_defaults(payload.model_dump(exclude_unset=True), facade)
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
        updates = _apply_defaults(payload.model_dump(exclude_unset=True), facade, existing=v)
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
        if bool(v.is_org):
            children = db.query(VendorModel).filter(VendorModel.organization_id == id)
            if cascade_children:
                children.delete(synchronize_session=False)
            else:
                children.update({"organization_id": None}, synchronize_session=False)

        db.delete(v)
        db.commit()
        return


# Mount façade routes
_crud_routes("/vendors", "vendors")
_crud_routes("/contacts", "contacts")
