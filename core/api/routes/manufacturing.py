# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import ManufacturingRunRequest, parse_run_request
from core.appdb.engine import get_session
from core.appdb.ledger import InsufficientStock
from core.config.writes import require_writes
from core.manufacturing.service import (
    append_run_journal,
    execute_run_txn,
    format_shortages,
    validate_run,
)
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


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
        append_run_journal(result["journal_entry"])
        return {
            "ok": True,
            "status": "completed",
            "run_id": result["run"].id,
            "output_unit_cost_cents": result["output_unit_cost_cents"],
        }
    except InsufficientStock as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail={"shortages": format_shortages(exc.shortages)})
    except HTTPException:
        db.rollback()
        raise
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=500, detail={"status": "failed_error"})
