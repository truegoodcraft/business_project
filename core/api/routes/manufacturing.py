# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import ManufacturingRunRequest, parse_run_request
from core.appdb.engine import get_session
from core.appdb.ledger import InsufficientStock
from core.config.writes import require_writes
from core.journal.manufacturing import append_mfg_journal
from core.manufacturing.service import execute_run_txn, format_shortages, validate_run
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])
logger = logging.getLogger(__name__)


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

    try:
        output_item_id, required, k = validate_run(db, body)
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
        _append_journal(
            {
                "ts": int(time.time()),
                "type": "manufacturing_run",
                "run_id": None,
                "recipe_id": getattr(body, "recipe_id", None),
                "status": "failed",
                "shortages": shortages,
            }
        )
        raise HTTPException(status_code=400, detail={"shortages": shortages})
    except HTTPException:
        db.rollback()
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
