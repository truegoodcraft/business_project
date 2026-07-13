# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.appdb.models import Item, Vendor
from core.appdb.models_jobs import Job, JobEvent, JobLine
from core.appdb.models_recipes import Recipe
from core.metrics.metric import allowed_units_for, normalize_quantity_to_base_int

JOB_STATUSES = {"draft", "active", "blocked", "ready", "done", "cancelled"}
CLOSED_JOB_STATUSES = {"done", "cancelled"}
JOB_LINE_TYPES = {"product", "service", "fee", "note"}
JOB_LINE_STATUSES = {"pending", "produced", "delivered", "cancelled"}


def _clean_required_text(value: str | None, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field}_required")
    return text


def _validate_job_status(status: str) -> str:
    value = (status or "").strip().lower()
    if value not in JOB_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_job_status")
    return value


def _validate_line_type(line_type: str) -> str:
    value = (line_type or "").strip().lower()
    if value not in JOB_LINE_TYPES:
        raise HTTPException(status_code=400, detail="invalid_job_line_type")
    return value


def _validate_line_status(status: str) -> str:
    value = (status or "").strip().lower()
    if value not in JOB_LINE_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_job_line_status")
    return value


def _validate_unit_price_cents(value: Any) -> int | None:
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail="unit_price_cents_invalid") from exc
    if (
        not decimal_value.is_finite()
        or decimal_value < 0
        or decimal_value != decimal_value.to_integral_value()
    ):
        raise HTTPException(status_code=400, detail="unit_price_cents_invalid")
    return int(decimal_value)


def _get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, int(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job


def _get_job_line(db: Session, job_id: int, line_id: int) -> JobLine:
    line = db.get(JobLine, int(line_id))
    if line is None or int(line.job_id) != int(job_id):
        raise HTTPException(status_code=404, detail="job_line_not_found")
    return line


def _validate_contact(db: Session, contact_id: int | None) -> None:
    if contact_id is None:
        return
    if db.get(Vendor, int(contact_id)) is None:
        raise HTTPException(status_code=404, detail="contact_not_found")


def _validate_item_recipe(db: Session, item_id: int | None, recipe_id: int | None) -> tuple[Item | None, Recipe | None]:
    item = db.get(Item, int(item_id)) if item_id is not None else None
    if item_id is not None and item is None:
        raise HTTPException(status_code=404, detail="item_not_found")

    recipe = db.get(Recipe, int(recipe_id)) if recipe_id is not None else None
    if recipe_id is not None and recipe is None:
        raise HTTPException(status_code=404, detail="recipe_not_found")
    return item, recipe


def _quantity_authority_item(db: Session, item: Item | None, recipe: Recipe | None) -> Item | None:
    if item is not None:
        return item
    if recipe is None:
        return None
    output_item = db.get(Item, int(recipe.output_item_id)) if recipe.output_item_id is not None else None
    if output_item is None:
        raise HTTPException(status_code=400, detail="recipe_output_item_not_found")
    return output_item


def _normalize_line_quantity(
    db: Session,
    *,
    line_type: str,
    item_id: int | None,
    recipe_id: int | None,
    quantity_decimal: str | None,
    uom: str | None,
) -> tuple[int | None, str | None]:
    if quantity_decimal is None:
        return None, uom
    display_uom = str(uom or "").strip().lower()
    if not display_uom:
        raise HTTPException(status_code=400, detail="uom_required")

    if line_type == "note":
        raise HTTPException(status_code=400, detail="quantity_not_allowed_for_note_line")

    item, recipe = _validate_item_recipe(db, item_id, recipe_id)
    authority_item = _quantity_authority_item(db, item, recipe)
    if authority_item is None:
        if line_type not in {"service", "fee"}:
            raise HTTPException(status_code=400, detail="item_or_recipe_required_for_quantity")
        if display_uom != "ea":
            raise HTTPException(status_code=400, detail="invalid_uom")
        dimension = "count"
    else:
        dimension = str(authority_item.dimension)

    if display_uom not in allowed_units_for(dimension):
        raise HTTPException(status_code=400, detail="invalid_uom")

    try:
        qty_base = normalize_quantity_to_base_int(
            quantity_decimal=str(quantity_decimal),
            uom=display_uom,
            dimension=dimension,
        )
    except ValueError as exc:
        if str(exc) == "unsupported_uom":
            raise HTTPException(status_code=400, detail="invalid_uom") from exc
        raise HTTPException(status_code=400, detail="invalid_quantity") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_quantity") from exc
    if qty_base <= 0:
        raise HTTPException(status_code=400, detail="quantity_decimal_must_be_positive")
    return int(qty_base), display_uom


def _normalize_meta(meta: Any) -> str | None:
    if meta is None:
        return None
    if isinstance(meta, str):
        try:
            json.loads(meta)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="meta_must_be_json") from exc
        return meta
    try:
        return json.dumps(meta, separators=(",", ":"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="meta_must_be_json") from exc


def _apply_closed_at(job: Job, status: str) -> None:
    if status in CLOSED_JOB_STATUSES:
        if job.closed_at is None:
            job.closed_at = datetime.utcnow()
    else:
        job.closed_at = None


def _add_event(
    db: Session,
    job_id: int,
    *,
    event_type: str,
    message: str,
    source_kind: str | None = None,
    source_id: str | None = None,
    meta: Any = None,
) -> JobEvent:
    event = JobEvent(
        job_id=int(job_id),
        event_type=_clean_required_text(event_type, "event_type"),
        message=_clean_required_text(message, "message"),
        source_kind=(source_kind or None),
        source_id=(source_id or None),
        meta=_normalize_meta(meta),
    )
    db.add(event)
    return event


def _contact_display(db: Session, contact_id: int | None) -> str | None:
    if contact_id is None:
        return None
    contact = db.get(Vendor, int(contact_id))
    if contact is None:
        return None
    return contact.name or contact.contact


def serialize_line(line: JobLine) -> dict[str, Any]:
    return {
        "id": line.id,
        "job_id": line.job_id,
        "item_id": line.item_id,
        "recipe_id": line.recipe_id,
        "line_type": line.line_type,
        "description": line.description,
        "qty_base": line.qty_base,
        "display_uom": line.display_uom,
        "unit_price_cents": line.unit_price_cents,
        "status": line.status,
        "sort_order": line.sort_order,
        "created_at": line.created_at,
        "updated_at": line.updated_at,
    }


def serialize_event(event: JobEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "job_id": event.job_id,
        "event_type": event.event_type,
        "message": event.message,
        "source_kind": event.source_kind,
        "source_id": event.source_id,
        "meta": event.meta,
        "created_at": event.created_at,
    }


def serialize_summary(db: Session, job: Job) -> dict[str, Any]:
    line_count = int(db.query(func.count(JobLine.id)).filter(JobLine.job_id == job.id).scalar() or 0)
    estimated_value_cents = int(
        db.query(func.coalesce(func.sum(JobLine.unit_price_cents), 0))
        .filter(JobLine.job_id == job.id, JobLine.unit_price_cents.isnot(None))
        .scalar()
        or 0
    )
    return {
        "id": job.id,
        "title": job.title,
        "status": job.status,
        "priority": job.priority,
        "due_date": job.due_date,
        "contact_id": job.contact_id,
        "contact_display": _contact_display(db, job.contact_id),
        "line_count": line_count,
        "estimated_value_cents": estimated_value_cents,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "closed_at": job.closed_at,
    }


def serialize_detail(db: Session, job: Job) -> dict[str, Any]:
    detail = serialize_summary(db, job)
    detail["notes"] = job.notes
    detail["lines"] = [
        serialize_line(line)
        for line in db.query(JobLine).filter(JobLine.job_id == job.id).order_by(JobLine.sort_order, JobLine.id).all()
    ]
    detail["events"] = [
        serialize_event(event)
        for event in db.query(JobEvent).filter(JobEvent.job_id == job.id).order_by(JobEvent.created_at, JobEvent.id).all()
    ]
    return detail


def list_jobs(db: Session, *, status: str | None = None, contact_id: int | None = None, q: str | None = None):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == _validate_job_status(status))
    if contact_id is not None:
        query = query.filter(Job.contact_id == int(contact_id))
    if q:
        like = f"%{q.strip()}%"
        query = query.outerjoin(Vendor, Vendor.id == Job.contact_id).filter(
            or_(Job.title.ilike(like), Job.notes.ilike(like), Vendor.name.ilike(like), Vendor.contact.ilike(like))
        )
    jobs = query.order_by(Job.priority.desc(), Job.due_date.asc(), Job.id.desc()).all()
    return [serialize_summary(db, job) for job in jobs]


def create_job(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    status = _validate_job_status(payload.get("status") or "draft")
    contact_id = payload.get("contact_id")
    _validate_contact(db, contact_id)

    job = Job(
        contact_id=contact_id,
        title=_clean_required_text(payload.get("title"), "title"),
        status=status,
        priority=int(payload.get("priority") or 0),
        due_date=payload.get("due_date"),
        notes=payload.get("notes"),
    )
    _apply_closed_at(job, status)
    db.add(job)
    db.flush()
    _add_event(db, int(job.id), event_type="job.created", message="Job created.")
    db.commit()
    db.refresh(job)
    return serialize_detail(db, job)


def update_job(db: Session, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    job = _get_job(db, job_id)
    if "status" in payload:
        _validate_job_status(payload["status"])
        raise HTTPException(status_code=400, detail="use_status_endpoint")
    if "contact_id" in payload:
        _validate_contact(db, payload["contact_id"])
        job.contact_id = payload["contact_id"]
    if "title" in payload:
        job.title = _clean_required_text(payload["title"], "title")
    if "priority" in payload and payload["priority"] is not None:
        job.priority = int(payload["priority"])
    if "due_date" in payload:
        job.due_date = payload["due_date"]
    if "notes" in payload:
        job.notes = payload["notes"]
    _add_event(db, int(job.id), event_type="job.updated", message="Job updated.")
    db.commit()
    db.refresh(job)
    return serialize_detail(db, job)


def transition_job_status(db: Session, job_id: int, status: str) -> dict[str, Any]:
    job = _get_job(db, job_id)
    previous_status = job.status
    next_status = _validate_job_status(status)
    job.status = next_status
    _apply_closed_at(job, next_status)
    _add_event(
        db,
        int(job.id),
        event_type="job.status_changed",
        message=f"Job status changed from {previous_status} to {next_status}.",
        meta={"previous_status": previous_status, "status": next_status},
    )
    db.commit()
    db.refresh(job)
    return serialize_detail(db, job)


def create_line(db: Session, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    job = _get_job(db, job_id)
    line_type = _validate_line_type(payload.get("line_type"))
    status = _validate_line_status(payload.get("status") or "pending")
    item_id = payload.get("item_id")
    recipe_id = payload.get("recipe_id")
    _validate_item_recipe(db, item_id, recipe_id)
    qty_base, display_uom = _normalize_line_quantity(
        db,
        line_type=line_type,
        item_id=item_id,
        recipe_id=recipe_id,
        quantity_decimal=payload.get("quantity_decimal"),
        uom=payload.get("uom"),
    )
    line = JobLine(
        job_id=int(job.id),
        item_id=item_id,
        recipe_id=recipe_id,
        line_type=line_type,
        description=_clean_required_text(payload.get("description"), "description"),
        qty_base=qty_base,
        display_uom=display_uom,
        unit_price_cents=_validate_unit_price_cents(payload.get("unit_price_cents")),
        status=status,
        sort_order=int(payload.get("sort_order") or 0),
    )
    db.add(line)
    db.flush()
    _add_event(
        db,
        int(job.id),
        event_type="job.line_created",
        message=f"Job line {line.id} created.",
        source_kind="job_line",
        source_id=str(line.id),
    )
    db.commit()
    db.refresh(line)
    return serialize_line(line)


def update_line(db: Session, job_id: int, line_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    line = _get_job_line(db, job_id, line_id)
    item_id = payload.get("item_id", line.item_id)
    recipe_id = payload.get("recipe_id", line.recipe_id)
    line_type = _validate_line_type(payload.get("line_type", line.line_type))
    _validate_item_recipe(db, item_id, recipe_id)
    if ("item_id" in payload or "recipe_id" in payload) and line.qty_base is not None and "quantity_decimal" not in payload:
        raise HTTPException(status_code=400, detail="quantity_required_when_quantity_authority_changes")

    if "line_type" in payload:
        line.line_type = line_type
    if "description" in payload:
        line.description = _clean_required_text(payload["description"], "description")
    if "item_id" in payload:
        line.item_id = payload["item_id"]
    if "recipe_id" in payload:
        line.recipe_id = payload["recipe_id"]
    if "unit_price_cents" in payload:
        line.unit_price_cents = _validate_unit_price_cents(payload["unit_price_cents"])
    if "status" in payload:
        line.status = _validate_line_status(payload["status"])
    if "sort_order" in payload and payload["sort_order"] is not None:
        line.sort_order = int(payload["sort_order"])

    if "quantity_decimal" in payload:
        if payload["quantity_decimal"] is None:
            line.qty_base = None
            line.display_uom = payload.get("uom")
        else:
            qty_base, display_uom = _normalize_line_quantity(
                db,
                line_type=line_type,
                item_id=item_id,
                recipe_id=recipe_id,
                quantity_decimal=payload["quantity_decimal"],
                uom=payload.get("uom"),
            )
            line.qty_base = qty_base
            line.display_uom = display_uom
    elif "uom" in payload:
        line.display_uom = payload["uom"]

    _add_event(
        db,
        int(job_id),
        event_type="job.line_updated",
        message=f"Job line {line.id} updated.",
        source_kind="job_line",
        source_id=str(line.id),
    )
    db.commit()
    db.refresh(line)
    return serialize_line(line)


def delete_line(db: Session, job_id: int, line_id: int) -> dict[str, Any]:
    line = _get_job_line(db, job_id, line_id)
    _add_event(
        db,
        int(job_id),
        event_type="job.line_deleted",
        message=f"Job line {line.id} deleted.",
        source_kind="job_line",
        source_id=str(line.id),
    )
    db.delete(line)
    db.commit()
    return {"ok": True, "deleted": int(line_id)}


def create_event(db: Session, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    job = _get_job(db, job_id)
    event = _add_event(
        db,
        int(job.id),
        event_type=payload.get("event_type"),
        message=payload.get("message"),
        source_kind=payload.get("source_kind"),
        source_id=payload.get("source_id"),
        meta=payload.get("meta"),
    )
    db.commit()
    db.refresh(event)
    return serialize_event(event)


def get_job_detail(db: Session, job_id: int) -> dict[str, Any]:
    return serialize_detail(db, _get_job(db, job_id))
