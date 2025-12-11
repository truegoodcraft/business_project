# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import logging
import time
from typing import Any, Iterable

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import ManufacturingRunRequest, parse_run_request
from core.appdb.engine import get_session
from core.appdb.ledger import InsufficientStock
from core.appdb.models_recipes import Recipe
from core.config.writes import require_writes
from core.journal.manufacturing import append_mfg_journal
from core.manufacturing.service import execute_run_txn, format_shortages, validate_run
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])
logger = logging.getLogger(__name__)


def _map_shortages(shortages: Iterable[dict]) -> list[dict]:
    return [
        {
            "component": int(s.get("item_id")) if s.get("item_id") is not None else None,
            "required": float(s.get("required", 0.0)),
            "available": float(s.get("available", s.get("on_hand", 0.0))),
        }
        for s in shortages
    ]


def _record_failed_run(
    db: Session, body: ManufacturingRunRequest, output_item_id: int | None, shortages: list[dict]
):
    from core.appdb.models_recipes import ManufacturingRun

    run = ManufacturingRun(
        recipe_id=getattr(body, "recipe_id", None),
        output_item_id=output_item_id or getattr(body, "output_item_id", None),
        output_qty=getattr(body, "output_qty", 0.0),
        status="failed_insufficient_stock",
        notes=getattr(body, "notes", None),
        meta=json.dumps({"shortages": shortages}),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _shortage_detail(shortages: list[dict], run_id: int | None) -> dict:
    return {
        "error": "insufficient_stock",
        "message": "Insufficient stock for required components.",
        "shortages": _map_shortages(shortages),
        "run_id": run_id,
    }


@router.post("/run")
async def run_manufacturing(
    req: Request,
    raw_body: Any = Body(...),
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)

    body: ManufacturingRunRequest = parse_run_request(raw_body)
    output_item_id: int | None = getattr(body, "output_item_id", None)

    recipe: Recipe | None = None
    if getattr(body, "recipe_id", None) is not None:
        recipe = db.get(Recipe, body.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if recipe.archived:
            raise HTTPException(status_code=400, detail="Recipe is archived")
        if not recipe.output_item_id:
            raise HTTPException(status_code=400, detail="Recipe has no output item")
        if recipe.output_qty <= 0:
            raise HTTPException(status_code=400, detail="Recipe has invalid output quantity")
        output_item_id = recipe.output_item_id

    try:
        output_item_id, required, k, shortages = validate_run(db, body)
        if shortages:
            run = _record_failed_run(db, body, output_item_id, shortages)
            _append_journal(
                {
                    "ts": int(time.time()),
                    "type": "manufacturing_run",
                    "run_id": run.id,
                    "recipe_id": getattr(body, "recipe_id", None),
                    "status": "failed_insufficient_stock",
                    "shortages": shortages,
                }
            )
            raise HTTPException(status_code=400, detail=_shortage_detail(shortages, run.id))
        result = execute_run_txn(db, body, output_item_id, required, k)
        _append_journal(
            {
                "ts": int(time.time()),
                "type": "manufacturing_run",
                "run_id": result["run"].id,
                "recipe_id": getattr(body, "recipe_id", None),
                "status": "success",
                "output_qty": body.output_qty,
            }
        )
        return {
            "ok": True,
            "status": "completed",
            "run_id": result["run"].id,
            "output_unit_cost_cents": result["output_unit_cost_cents"],
        }
    except InsufficientStock as exc:
        db.rollback()
        shortages = format_shortages(exc.shortages)
        run = _record_failed_run(db, body, output_item_id, shortages)
        _append_journal(
            {
                "ts": int(time.time()),
                "type": "manufacturing_run",
                "run_id": run.id,
                "recipe_id": getattr(body, "recipe_id", None),
                "status": "failed_insufficient_stock",
                "shortages": shortages,
            }
        )
        raise HTTPException(status_code=400, detail=_shortage_detail(shortages, run.id))
    except HTTPException as exc:
        db.rollback()
        detail = exc.detail

        if isinstance(detail, dict) and detail.get("error") == "insufficient_stock":
            raise

        shortages: list[dict] | None = None
        if isinstance(detail, dict) and detail.get("shortages"):
            shortages = format_shortages(detail.get("shortages", []))

        if shortages is not None:
            run = _record_failed_run(db, body, output_item_id, shortages)
            _append_journal(
                {
                    "ts": int(time.time()),
                    "type": "manufacturing_run",
                    "run_id": run.id,
                    "recipe_id": getattr(body, "recipe_id", None),
                    "status": "failed_insufficient_stock",
                    "shortages": shortages,
                }
            )
            raise HTTPException(status_code=400, detail=_shortage_detail(shortages, run.id))

        _append_journal(
            {
                "ts": int(time.time()),
                "type": "manufacturing_run",
                "run_id": None,
                "recipe_id": getattr(body, "recipe_id", None),
                "status": "failed",
            }
        )
        raise
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=500, detail={"status": "failed_error"})


def _append_journal(entry: dict) -> None:
    try:
        append_mfg_journal(entry)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to append manufacturing journal entry")
