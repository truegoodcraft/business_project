# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.api.utils.quantity_guard import reject_legacy_qty_keys
from core.appdb.engine import get_session
from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_JOBS_READ, PERMISSION_JOBS_WRITE
from core.config.writes import require_writes
from core.services import invoices as invoice_service
from core.policy.guard import require_owner_commit
from core.services import jobs as jobs_service
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    title: str
    contact_id: int | None = None
    status: str = "draft"
    priority: int = 0
    due_date: datetime | None = None
    notes: str | None = None


class JobUpdateRequest(BaseModel):
    title: str | None = None
    contact_id: int | None = None
    status: str | None = None
    priority: int | None = None
    due_date: datetime | None = None
    notes: str | None = None


class JobStatusRequest(BaseModel):
    status: str


class JobLineCreateRequest(BaseModel):
    item_id: int | None = None
    recipe_id: int | None = None
    line_type: str
    description: str
    quantity_decimal: str | None = None
    uom: str | None = None
    unit_price_cents: int | None = None
    status: str = "pending"
    sort_order: int = 0


class JobLineUpdateRequest(BaseModel):
    item_id: int | None = None
    recipe_id: int | None = None
    line_type: str | None = None
    description: str | None = None
    quantity_decimal: str | None = None
    uom: str | None = None
    unit_price_cents: int | None = None
    status: str | None = None
    sort_order: int | None = None


class JobEventCreateRequest(BaseModel):
    event_type: str
    message: str
    source_kind: str | None = None
    source_id: str | None = None
    meta: Any = None


class JobInvoiceCreateRequest(BaseModel):
    due_date: datetime | None = None
    tax_rate_percent: str | None = None
    notes: str | None = None


@router.get("")
def list_jobs(
    status: str | None = Query(None),
    contact_id: int | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_JOBS_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return jobs_service.list_jobs(db, status=status, contact_id=contact_id, q=q)


@router.post("")
def create_job(
    req: Request,
    body: JobCreateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    return jobs_service.create_job(db, body.model_dump())


@router.get("/{job_id}")
def get_job_detail(
    job_id: int,
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_JOBS_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return jobs_service.get_job_detail(db, job_id)


@router.patch("/{job_id}")
def patch_job(
    job_id: int,
    req: Request,
    body: JobUpdateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    return jobs_service.update_job(db, job_id, body.model_dump(exclude_unset=True))


@router.post("/{job_id}/lines")
def create_job_line(
    job_id: int,
    req: Request,
    raw: dict = Body(...),
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    reject_legacy_qty_keys(raw)
    body = JobLineCreateRequest(**raw)
    return jobs_service.create_line(db, job_id, body.model_dump())


@router.patch("/{job_id}/lines/{line_id}")
def patch_job_line(
    job_id: int,
    line_id: int,
    req: Request,
    raw: dict = Body(...),
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    reject_legacy_qty_keys(raw)
    body = JobLineUpdateRequest(**raw)
    return jobs_service.update_line(db, job_id, line_id, body.model_dump(exclude_unset=True))


@router.delete("/{job_id}/lines/{line_id}")
def delete_job_line(
    job_id: int,
    line_id: int,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    return jobs_service.delete_line(db, job_id, line_id)


@router.post("/{job_id}/events")
def create_job_event(
    job_id: int,
    req: Request,
    body: JobEventCreateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    return jobs_service.create_event(db, job_id, body.model_dump())


@router.post("/{job_id}/status")
def transition_job_status(
    job_id: int,
    req: Request,
    body: JobStatusRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    return jobs_service.transition_job_status(db, job_id, body.status)


@router.post("/{job_id}/invoice")
def create_job_invoice(
    job_id: int,
    body: JobInvoiceCreateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_JOBS_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.create_invoice_from_job(db, job_id, body.model_dump(exclude_unset=True))
