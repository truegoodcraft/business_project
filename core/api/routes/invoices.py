# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.auth.dependencies import require_permission
from core.auth.permissions import PERMISSION_INVOICES_READ, PERMISSION_INVOICES_WRITE
from core.config.writes import require_writes
from core.services import invoices as invoice_service
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/invoices", tags=["invoices"])


class InvoiceCreateRequest(BaseModel):
    contact_id: int
    job_id: int | None = None
    due_date: datetime | None = None
    tax_rate_percent: str | None = None
    notes: str | None = None


class InvoiceUpdateRequest(BaseModel):
    contact_id: int | None = None
    job_id: int | None = None
    due_date: datetime | None = None
    tax_rate_percent: str | None = None
    notes: str | None = None


class InvoiceLineCreateRequest(BaseModel):
    job_line_id: int | None = None
    item_id: int | None = None
    line_type: str
    description: str
    quantity_decimal: str | None = None
    uom: str | None = None
    unit_price_cents: int | None = None
    taxable: bool = True
    sort_order: int = 0


class InvoiceLineUpdateRequest(BaseModel):
    job_line_id: int | None = None
    item_id: int | None = None
    line_type: str | None = None
    description: str | None = None
    quantity_decimal: str | None = None
    uom: str | None = None
    unit_price_cents: int | None = None
    taxable: bool | None = None
    sort_order: int | None = None


class InvoiceIssueRequest(BaseModel):
    issue_date: datetime | None = None


class InvoiceMarkPaidRequest(BaseModel):
    paid_at: datetime | None = None
    notes: str | None = None


@router.get("")
def list_invoices(
    status: str | None = Query(None),
    contact_id: int | None = Query(None),
    job_id: int | None = Query(None),
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_INVOICES_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.list_invoices(db, status=status, contact_id=contact_id, job_id=job_id)


@router.post("")
def create_invoice(
    body: InvoiceCreateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.create_invoice(db, body.model_dump())


@router.get("/{invoice_id}")
def get_invoice_detail(
    invoice_id: int,
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_INVOICES_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.get_invoice_detail(db, invoice_id)


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def get_invoice_print(
    invoice_id: int,
    db: Session = Depends(get_session),
    _permission=Depends(require_permission(PERMISSION_INVOICES_READ)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return HTMLResponse(invoice_service.render_invoice_print_html(db, invoice_id))


@router.patch("/{invoice_id}")
def patch_invoice(
    invoice_id: int,
    body: InvoiceUpdateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.update_invoice(db, invoice_id, body.model_dump(exclude_unset=True))


@router.post("/{invoice_id}/lines")
def create_invoice_line(
    invoice_id: int,
    body: InvoiceLineCreateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.add_invoice_line(db, invoice_id, body.model_dump())


@router.patch("/{invoice_id}/lines/{line_id}")
def patch_invoice_line(
    invoice_id: int,
    line_id: int,
    body: InvoiceLineUpdateRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.update_invoice_line(db, invoice_id, line_id, body.model_dump(exclude_unset=True))


@router.delete("/{invoice_id}/lines/{line_id}")
def delete_invoice_line(
    invoice_id: int,
    line_id: int,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.delete_invoice_line(db, invoice_id, line_id)


@router.post("/{invoice_id}/issue")
def issue_invoice(
    invoice_id: int,
    body: InvoiceIssueRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.issue_invoice(db, invoice_id, body.model_dump(exclude_unset=True))


@router.post("/{invoice_id}/mark-paid")
def mark_invoice_paid(
    invoice_id: int,
    body: InvoiceMarkPaidRequest,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.mark_invoice_paid(db, invoice_id, body.model_dump(exclude_unset=True))


@router.post("/{invoice_id}/void")
def void_invoice(
    invoice_id: int,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _permission=Depends(require_permission(PERMISSION_INVOICES_WRITE)),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    return invoice_service.void_invoice(db, invoice_id)
