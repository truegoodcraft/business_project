# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from html import escape
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.appdb.models import CashEvent, Item, Vendor
from core.appdb.models_invoices import DocumentSequence, Invoice, InvoiceLine
from core.appdb.models_jobs import Job, JobLine
from core.appdb.models_recipes import Recipe
from core.metrics.metric import from_base

INVOICE_STATUSES = {"draft", "issued", "paid", "void"}
INVOICE_LINE_TYPES = {"product", "service", "fee", "note"}
BILLABLE_JOB_LINE_TYPES = {"product", "service", "fee"}
MAX_TAX_BASIS_POINTS = 1_000_000


def _clean_required_text(value: str | None, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field}_required")
    return text


def _parse_optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _parse_decimal(value: str | None, *, allow_null: bool = True) -> Decimal | None:
    text = _parse_optional_text(value)
    if text is None:
        if allow_null:
            return None
        raise HTTPException(status_code=400, detail="quantity_decimal_required")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail="quantity_decimal_invalid") from exc


def _round_to_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _tax_basis_points_from_percent(value: Any) -> int:
    if value is None:
        return 0
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail="tax_rate_percent_invalid") from exc
    if decimal_value < 0:
        raise HTTPException(status_code=400, detail="tax_rate_percent_invalid")
    basis_points = _round_to_cents(decimal_value * Decimal("100"))
    if basis_points > MAX_TAX_BASIS_POINTS:
        raise HTTPException(status_code=400, detail="tax_rate_basis_points_invalid")
    return int(basis_points)


def _tax_percent_from_basis_points(value: int) -> str:
    return format((Decimal(int(value)) / Decimal("100")).normalize(), "f")


def _validate_line_type(line_type: str) -> str:
    normalized = (line_type or "").strip().lower()
    if normalized not in INVOICE_LINE_TYPES:
        raise HTTPException(status_code=400, detail="invalid_invoice_line_type")
    return normalized


def _get_contact(db: Session, contact_id: int) -> Vendor:
    contact = db.get(Vendor, int(contact_id))
    if contact is None:
        raise HTTPException(status_code=404, detail="invoice_contact_not_found")
    return contact


def _get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, int(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="invoice_job_not_found")
    return job


def _get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.get(Invoice, int(invoice_id))
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    return invoice


def _get_invoice_line(db: Session, invoice_id: int, line_id: int) -> InvoiceLine:
    line = db.get(InvoiceLine, int(line_id))
    if line is None or int(line.invoice_id) != int(invoice_id):
        raise HTTPException(status_code=404, detail="invoice_line_not_found")
    return line


def _require_draft(invoice: Invoice) -> None:
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="invoice_edit_forbidden_after_paid")
    if invoice.status == "void":
        raise HTTPException(status_code=400, detail="invoice_edit_forbidden_after_void")
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="invoice_edit_forbidden_after_issue")


def _serialize_invoice_line(line: InvoiceLine) -> dict[str, Any]:
    return {
        "id": int(line.id),
        "invoice_id": int(line.invoice_id),
        "job_line_id": int(line.job_line_id) if line.job_line_id is not None else None,
        "item_id": int(line.item_id) if line.item_id is not None else None,
        "line_type": line.line_type,
        "description": line.description,
        "quantity_decimal": line.quantity_decimal,
        "uom": line.uom,
        "unit_price_cents": int(line.unit_price_cents) if line.unit_price_cents is not None else None,
        "taxable": bool(line.taxable),
        "line_subtotal_cents": int(line.line_subtotal_cents or 0),
        "sort_order": int(line.sort_order or 0),
        "created_at": line.created_at,
        "updated_at": line.updated_at,
    }


def _serialize_invoice(invoice: Invoice, *, include_lines: bool = False) -> dict[str, Any]:
    payload = {
        "id": int(invoice.id),
        "invoice_number": invoice.invoice_number,
        "contact_id": int(invoice.contact_id),
        "job_id": int(invoice.job_id) if invoice.job_id is not None else None,
        "status": invoice.status,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "paid_at": invoice.paid_at,
        "voided_at": invoice.voided_at,
        "tax_rate_percent": _tax_percent_from_basis_points(int(invoice.tax_rate_basis_points or 0)),
        "subtotal_cents": int(invoice.subtotal_cents or 0),
        "tax_cents": int(invoice.tax_cents or 0),
        "total_cents": int(invoice.total_cents or 0),
        "paid_cash_event_id": int(invoice.paid_cash_event_id) if invoice.paid_cash_event_id is not None else None,
        "notes": invoice.notes,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
    }
    if include_lines:
        payload["lines"] = [_serialize_invoice_line(line) for line in sorted(invoice.lines, key=lambda row: (row.sort_order, row.id))]
    return payload


def generate_invoice_number(db: Session) -> str:
    sequence = db.get(DocumentSequence, "invoice")
    if sequence is None:
        sequence = DocumentSequence(key="invoice", next_number=1001)
        db.add(sequence)
        db.flush()
    next_number = max(1001, int(sequence.next_number))
    sequence.next_number = next_number + 1
    db.flush()
    return f"INV-{next_number}"


def _line_subtotal_cents(line: InvoiceLine) -> int:
    quantity = _parse_decimal(line.quantity_decimal, allow_null=True)
    if quantity is None:
        return int(line.line_subtotal_cents or 0)
    if quantity < 0:
        raise HTTPException(status_code=400, detail="quantity_decimal_invalid")
    return _round_to_cents(quantity * Decimal(int(line.unit_price_cents or 0)))


def recalculate_invoice_totals(db: Session, invoice_id: int) -> dict[str, int]:
    invoice = _get_invoice(db, invoice_id)
    subtotal_cents = 0
    taxable_cents = 0
    for line in invoice.lines:
        line.line_subtotal_cents = _line_subtotal_cents(line)
        subtotal_cents += int(line.line_subtotal_cents or 0)
        if bool(line.taxable):
            taxable_cents += int(line.line_subtotal_cents or 0)
    tax_cents = _round_to_cents(
        Decimal(taxable_cents) * Decimal(int(invoice.tax_rate_basis_points or 0)) / Decimal("10000")
    )
    invoice.subtotal_cents = int(subtotal_cents)
    invoice.tax_cents = int(tax_cents)
    invoice.total_cents = int(subtotal_cents + tax_cents)
    db.flush()
    return {
        "subtotal_cents": int(invoice.subtotal_cents),
        "tax_cents": int(invoice.tax_cents),
        "total_cents": int(invoice.total_cents),
    }


def list_invoices(db: Session, *, status: str | None = None, contact_id: int | None = None, job_id: int | None = None):
    query = db.query(Invoice)
    if status:
        normalized = (status or "").strip().lower()
        if normalized not in INVOICE_STATUSES:
            raise HTTPException(status_code=400, detail="invalid_invoice_status")
        query = query.filter(Invoice.status == normalized)
    if contact_id is not None:
        query = query.filter(Invoice.contact_id == int(contact_id))
    if job_id is not None:
        query = query.filter(Invoice.job_id == int(job_id))
    rows = query.order_by(Invoice.id.desc()).all()
    return [_serialize_invoice(row) for row in rows]


def create_invoice(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    contact_id = payload.get("contact_id")
    if contact_id is None:
        raise HTTPException(status_code=400, detail="invoice_contact_required")
    _get_contact(db, int(contact_id))
    job_id = payload.get("job_id")
    if job_id is not None:
        _get_job(db, int(job_id))
    invoice = Invoice(
        invoice_number=generate_invoice_number(db),
        contact_id=int(contact_id),
        job_id=int(job_id) if job_id is not None else None,
        status="draft",
        due_date=payload.get("due_date"),
        tax_rate_basis_points=_tax_basis_points_from_percent(payload.get("tax_rate_percent")),
        notes=payload.get("notes"),
    )
    db.add(invoice)
    db.flush()
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)


def _validate_line_payload(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    line_type = _validate_line_type(payload.get("line_type"))
    description = _clean_required_text(payload.get("description"), "description")
    quantity_decimal = _parse_optional_text(payload.get("quantity_decimal"))
    if quantity_decimal is not None:
        quantity = _parse_decimal(quantity_decimal, allow_null=False)
        if quantity is None or quantity < 0:
            raise HTTPException(status_code=400, detail="quantity_decimal_invalid")
    uom = _parse_optional_text(payload.get("uom"))
    if quantity_decimal is not None and uom is None:
        raise HTTPException(status_code=400, detail="uom_required")
    if quantity_decimal is None and uom is not None:
        raise HTTPException(status_code=400, detail="uom_requires_quantity_decimal")
    unit_price_cents = payload.get("unit_price_cents")
    if unit_price_cents is not None and int(unit_price_cents) < 0:
        raise HTTPException(status_code=400, detail="unit_price_cents_invalid")
    item_id = payload.get("item_id")
    if item_id is not None and db.get(Item, int(item_id)) is None:
        raise HTTPException(status_code=404, detail="invoice_item_not_found")
    job_line_id = payload.get("job_line_id")
    if job_line_id is not None and db.get(JobLine, int(job_line_id)) is None:
        raise HTTPException(status_code=404, detail="invoice_job_line_not_found")
    return {
        "line_type": line_type,
        "description": description,
        "quantity_decimal": quantity_decimal,
        "uom": uom,
        "unit_price_cents": int(unit_price_cents) if unit_price_cents is not None else None,
        "taxable": bool(payload.get("taxable", True)),
        "sort_order": int(payload.get("sort_order") or 0),
        "item_id": int(item_id) if item_id is not None else None,
        "job_line_id": int(job_line_id) if job_line_id is not None else None,
    }


def add_invoice_line(db: Session, invoice_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    _require_draft(invoice)
    line = InvoiceLine(invoice_id=int(invoice.id), **_validate_line_payload(db, payload))
    db.add(line)
    db.flush()
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    db.refresh(line)
    return _serialize_invoice_line(line)


def update_invoice_line(db: Session, invoice_id: int, line_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    _require_draft(invoice)
    line = _get_invoice_line(db, invoice_id, line_id)
    merged = {
        "line_type": payload.get("line_type", line.line_type),
        "description": payload.get("description", line.description),
        "quantity_decimal": payload.get("quantity_decimal", line.quantity_decimal),
        "uom": payload.get("uom", line.uom),
        "unit_price_cents": payload.get("unit_price_cents", line.unit_price_cents),
        "taxable": payload.get("taxable", line.taxable),
        "sort_order": payload.get("sort_order", line.sort_order),
        "item_id": payload.get("item_id", line.item_id),
        "job_line_id": payload.get("job_line_id", line.job_line_id),
    }
    for key, value in _validate_line_payload(db, merged).items():
        setattr(line, key, value)
    db.flush()
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    db.refresh(line)
    return _serialize_invoice_line(line)


def delete_invoice_line(db: Session, invoice_id: int, line_id: int) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    _require_draft(invoice)
    line = _get_invoice_line(db, invoice_id, line_id)
    db.delete(line)
    db.flush()
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    return {"ok": True, "deleted": int(line_id)}


def get_invoice_detail(db: Session, invoice_id: int) -> dict[str, Any]:
    return _serialize_invoice(_get_invoice(db, invoice_id), include_lines=True)


def _format_invoice_print_date(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text:
        return fallback
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return text


def _format_invoice_money(cents: Any) -> str:
    value = Decimal(int(cents or 0)) / Decimal("100")
    return f"CAD ${value:,.2f}"


def render_invoice_print_html(db: Session, invoice_id: int) -> str:
    invoice = get_invoice_detail(db, invoice_id)
    contact = _get_contact(db, int(invoice["contact_id"]))
    job = _get_job(db, int(invoice["job_id"])) if invoice.get("job_id") is not None else None

    lines_html = []
    for line in invoice.get("lines", []):
        taxable_label = "Yes" if line.get("taxable") else "No"
        lines_html.append(
            (
                "<tr>"
                f"<td>{escape(str(line.get('description') or ''))}</td>"
                f"<td>{escape(str(line.get('line_type') or ''))}</td>"
                f"<td>{escape(str(line.get('quantity_decimal') or '—'))}</td>"
                f"<td>{escape(str(line.get('uom') or '—'))}</td>"
                f"<td>{escape(_format_invoice_money(line.get('unit_price_cents')) if line.get('unit_price_cents') is not None else '—')}</td>"
                f"<td>{escape(taxable_label)}</td>"
                f"<td>{escape(_format_invoice_money(line.get('line_subtotal_cents')))}</td>"
                "</tr>"
            )
        )
    if not lines_html:
        lines_html.append('<tr><td colspan="7">No lines</td></tr>')

    notes_text = str(invoice.get("notes") or "").strip()
    notes_html = escape(notes_text) if notes_text else "—"
    contact_display = str(getattr(contact, "name", "") or f"Contact #{invoice['contact_id']}")
    job_display = str(getattr(job, "title", "") or f"Job #{invoice['job_id']}") if job is not None else "—"

    return (
        "<!doctype html>"
        "<html lang=\"en\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        f"<title>{escape(str(invoice.get('invoice_number') or f'Invoice #{invoice_id}'))}</title>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:32px;color:#111;background:#fff;}"
        "h1,h2,h3{margin:0 0 8px;}"
        ".page{max-width:960px;margin:0 auto;}"
        ".header{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:24px;}"
        ".muted{color:#555;font-size:14px;}"
        ".meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 24px;margin:20px 0;}"
        ".meta-block{border:1px solid #d0d0d0;padding:12px;border-radius:8px;}"
        ".label{display:block;font-size:12px;text-transform:uppercase;color:#666;margin-bottom:4px;}"
        "table{width:100%;border-collapse:collapse;margin-top:18px;}"
        "th,td{border:1px solid #d0d0d0;padding:10px;text-align:left;vertical-align:top;font-size:14px;}"
        "th{background:#f4f4f4;}"
        ".totals{margin-top:18px;margin-left:auto;width:min(320px,100%);}"
        ".totals-row{display:flex;justify-content:space-between;border-bottom:1px solid #d0d0d0;padding:8px 0;gap:12px;}"
        ".totals-row strong{font-size:16px;}"
        ".notes{margin-top:24px;border:1px solid #d0d0d0;border-radius:8px;padding:12px;white-space:pre-wrap;}"
        "@media screen and (max-width:700px){body{margin:16px;}.header{flex-direction:column;gap:10px;}"
        ".meta{grid-template-columns:1fr;}table{display:block;overflow-x:auto;white-space:nowrap;}}"
        "@media print{body{margin:16px;}.page{max-width:none;}tr{break-inside:avoid;}.notes{break-inside:avoid;}}"
        "</style>"
        "</head>"
        "<body>"
        "<div class=\"page\">"
        "<div class=\"header\">"
        "<div>"
        "<h1>Invoice</h1>"
        "<div class=\"muted\">Generated locally with BUS Core · All amounts CAD</div>"
        "</div>"
        "<div>"
        f"<h2>{escape(str(invoice.get('invoice_number') or f'Invoice #{invoice_id}'))}</h2>"
        f"<div class=\"muted\">Status: {escape(str(invoice.get('status') or 'draft'))}</div>"
        "</div>"
        "</div>"
        "<div class=\"meta\">"
        "<div class=\"meta-block\">"
        "<span class=\"label\">Customer / Contact</span>"
        f"<div>{escape(contact_display)}</div>"
        "</div>"
        "<div class=\"meta-block\">"
        "<span class=\"label\">Linked Job</span>"
        f"<div>{escape(job_display)}</div>"
        "</div>"
        "<div class=\"meta-block\">"
        "<span class=\"label\">Issue Date</span>"
        f"<div>{escape(_format_invoice_print_date(invoice.get('issue_date')))}</div>"
        "</div>"
        "<div class=\"meta-block\">"
        "<span class=\"label\">Due Date</span>"
        f"<div>{escape(_format_invoice_print_date(invoice.get('due_date')))}</div>"
        "</div>"
        "</div>"
        "<table>"
        "<thead><tr><th>Description</th><th>Type</th><th>Quantity</th><th>UOM</th><th>Unit Price</th><th>Taxable</th><th>Subtotal</th></tr></thead>"
        f"<tbody>{''.join(lines_html)}</tbody>"
        "</table>"
        "<div class=\"totals\">"
        f"<div class=\"totals-row\"><span>Subtotal</span><span>{escape(_format_invoice_money(invoice.get('subtotal_cents')))}</span></div>"
        f"<div class=\"totals-row\"><span>Tax Rate</span><span>{escape(str(invoice.get('tax_rate_percent') or '0'))}%</span></div>"
        f"<div class=\"totals-row\"><span>Tax Total</span><span>{escape(_format_invoice_money(invoice.get('tax_cents')))}</span></div>"
        f"<div class=\"totals-row\"><strong>Total</strong><strong>{escape(_format_invoice_money(invoice.get('total_cents')))}</strong></div>"
        "</div>"
        "<div class=\"notes\">"
        "<span class=\"label\">Notes</span>"
        f"{notes_html}"
        "</div>"
        "</div>"
        "</body>"
        "</html>"
    )


def update_invoice(db: Session, invoice_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    _require_draft(invoice)
    if "contact_id" in payload and payload.get("contact_id") is not None:
        _get_contact(db, int(payload["contact_id"]))
        invoice.contact_id = int(payload["contact_id"])
    if "job_id" in payload:
        if payload.get("job_id") is None:
            invoice.job_id = None
        else:
            _get_job(db, int(payload["job_id"]))
            invoice.job_id = int(payload["job_id"])
    if "due_date" in payload:
        invoice.due_date = payload["due_date"]
    if "notes" in payload:
        invoice.notes = payload["notes"]
    if "tax_rate_percent" in payload:
        invoice.tax_rate_basis_points = _tax_basis_points_from_percent(payload["tax_rate_percent"])
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)


def issue_invoice(db: Session, invoice_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="invoice_issue_forbidden_after_paid")
    if invoice.status == "void":
        raise HTTPException(status_code=400, detail="invoice_issue_forbidden_after_void")
    if not invoice.lines:
        raise HTTPException(status_code=400, detail="invoice_issue_requires_line")
    recalculate_invoice_totals(db, int(invoice.id))
    invoice.status = "issued"
    invoice.issue_date = (payload or {}).get("issue_date") or invoice.issue_date or datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)


def _existing_invoice_cash_event(db: Session, invoice_id: int) -> CashEvent | None:
    return (
        db.query(CashEvent)
        .filter(
            CashEvent.kind == "sale",
            CashEvent.source_kind == "invoice",
            CashEvent.source_id == f"invoice:{int(invoice_id)}",
        )
        .order_by(CashEvent.id.asc())
        .first()
    )


def mark_invoice_paid(db: Session, invoice_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    if invoice.status == "void":
        raise HTTPException(status_code=400, detail="invoice_void_cannot_be_paid")
    existing = db.get(CashEvent, int(invoice.paid_cash_event_id)) if invoice.paid_cash_event_id is not None else None
    if existing is None:
        existing = _existing_invoice_cash_event(db, invoice_id)
    if existing is not None:
        if invoice.paid_cash_event_id is None:
            invoice.paid_cash_event_id = int(existing.id)
        if invoice.status != "paid":
            invoice.status = "paid"
        if invoice.paid_at is None:
            invoice.paid_at = existing.created_at or datetime.utcnow()
        db.commit()
        db.refresh(invoice)
        return _serialize_invoice(invoice, include_lines=True)
    if invoice.status == "draft":
        raise HTTPException(status_code=400, detail="invoice_payment_requires_issue")
    recalculate_invoice_totals(db, int(invoice.id))
    paid_at = (payload or {}).get("paid_at") or datetime.utcnow()
    cash_event = CashEvent(
        kind="sale",
        category="invoice",
        amount_cents=int(invoice.total_cents or 0),
        item_id=None,
        qty_base=None,
        unit_price_cents=None,
        source_kind="invoice",
        source_id=f"invoice:{int(invoice.id)}",
        related_source_id=None,
        notes=(payload or {}).get("notes"),
        created_at=paid_at,
    )
    db.add(cash_event)
    db.flush()
    invoice.status = "paid"
    invoice.paid_at = paid_at
    invoice.paid_cash_event_id = int(cash_event.id)
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)


def void_invoice(db: Session, invoice_id: int) -> dict[str, Any]:
    invoice = _get_invoice(db, invoice_id)
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="invoice_paid_cannot_be_void")
    invoice.status = "void"
    invoice.voided_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)


def _job_line_quantity_decimal(db: Session, line: JobLine) -> str | None:
    if line.qty_base is None or line.display_uom is None:
        return None
    if line.item_id is not None:
        item = db.get(Item, int(line.item_id))
        if item is not None:
            return format(from_base(int(line.qty_base), line.display_uom, item.dimension).normalize(), "f")
    if line.recipe_id is not None:
        recipe = db.get(Recipe, int(line.recipe_id))
        if recipe is not None and recipe.output_item_id is not None:
            item = db.get(Item, int(recipe.output_item_id))
            if item is not None:
                return format(from_base(int(line.qty_base), line.display_uom, item.dimension).normalize(), "f")
    return format((Decimal(int(line.qty_base)) / Decimal("1000")).normalize(), "f")


def create_invoice_from_job(db: Session, job_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    job = _get_job(db, job_id)
    if job.contact_id is None:
        raise HTTPException(status_code=400, detail="invoice_job_contact_required")
    invoice = Invoice(
        invoice_number=generate_invoice_number(db),
        contact_id=int(job.contact_id),
        job_id=int(job.id),
        status="draft",
        due_date=(payload or {}).get("due_date") or job.due_date,
        tax_rate_basis_points=_tax_basis_points_from_percent((payload or {}).get("tax_rate_percent")),
        notes=(payload or {}).get("notes"),
    )
    db.add(invoice)
    db.flush()
    lines = (
        db.query(JobLine)
        .filter(JobLine.job_id == int(job.id))
        .filter(JobLine.line_type.in_(list(BILLABLE_JOB_LINE_TYPES)))
        .filter(JobLine.status != "cancelled")
        .order_by(JobLine.sort_order.asc(), JobLine.id.asc())
        .all()
    )
    for line in lines:
        db.add(
            InvoiceLine(
                invoice_id=int(invoice.id),
                job_line_id=int(line.id),
                item_id=int(line.item_id) if line.item_id is not None else None,
                line_type=line.line_type,
                description=line.description,
                quantity_decimal=_job_line_quantity_decimal(db, line),
                uom=line.display_uom,
                unit_price_cents=int(line.unit_price_cents) if line.unit_price_cents is not None else None,
                taxable=True,
                sort_order=int(line.sort_order or 0),
            )
        )
    db.flush()
    recalculate_invoice_totals(db, int(invoice.id))
    db.commit()
    db.refresh(invoice)
    return _serialize_invoice(invoice, include_lines=True)
