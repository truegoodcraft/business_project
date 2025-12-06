# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
import json
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import ManufacturingRunRequest, parse_run_request
from core.appdb.engine import get_session
from core.appdb.ledger import InsufficientStock, add_batch, fifo_consume, on_hand_qty
from core.appdb.models_recipes import ManufacturingRun
from core.config.writes import require_writes
from core.manufacturing.service import format_shortages, validate_run
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

    output_item_id, required, k = validate_run(db, body)

    run = ManufacturingRun(
        recipe_id=getattr(body, "recipe_id", None),
        output_item_id=output_item_id,
        output_qty=body.output_qty,
        status="created",
        notes=getattr(body, "notes", None),
    )
    db.add(run)
    db.flush()

    cost_inputs_cents = 0
    try:
        for r in required:
            if r["qty"] <= 0:
                continue
            if r["is_optional"]:
                if on_hand_qty(db, r["item_id"]) + 1e-9 < r["qty"]:
                    continue
            pre_oh = on_hand_qty(db, r["item_id"])
            if pre_oh + 1e-9 < r["qty"] and not r["is_optional"]:
                raise InsufficientStock(
                    [
                        {
                            "item_id": r["item_id"],
                            "required": r["qty"],
                            "on_hand": pre_oh,
                            "missing": r["qty"] - pre_oh,
                        }
                    ]
                )
            movements = fifo_consume(db, r["item_id"], r["qty"], source_kind="manufacturing", source_id=run.id)
            for mv in movements:
                if mv.unit_cost_cents is not None:
                    cost_inputs_cents += int(mv.unit_cost_cents * abs(mv.qty_change))

        per_output_cents = int(round(cost_inputs_cents / max(body.output_qty, 1e-9)))
        add_batch(db, output_item_id, body.output_qty, per_output_cents, source_kind="manufacturing", source_id=run.id)

        run.status = "completed"
        run.executed_at = datetime.utcnow()
        run.meta = json.dumps(
            {"k": k, "cost_inputs_cents": cost_inputs_cents, "per_output_cents": per_output_cents}
        )
        db.commit()
        return {"ok": True, "status": "completed", "run_id": run.id}
    except InsufficientStock as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail={"shortages": format_shortages(exc.shortages)})
    except HTTPException:
        db.rollback()
        raise
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=500, detail={"status": "failed_error"})
