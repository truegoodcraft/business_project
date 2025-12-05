# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.appdb.ledger import InsufficientStock, add_batch, fifo_consume, on_hand_qty
from core.appdb.models_recipes import ManufacturingRun, Recipe, RecipeItem
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


class ComponentInput(BaseModel):
    item_id: int
    qty_required: float = Field(..., gt=0)
    is_optional: bool = False


class RunInput(BaseModel):
    recipe_id: Optional[int] = None
    output_item_id: Optional[int] = None
    output_qty: float = Field(..., gt=0)
    notes: Optional[str] = None
    components: Optional[List[ComponentInput]] = None


@router.post("/run")
async def run_manufacturing(
    body: RunInput,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)

    if body.recipe_id:
        recipe = db.get(Recipe, body.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if not recipe.output_item_id:
            raise HTTPException(status_code=400, detail="Recipe has no output_item_id")
        output_item_id = recipe.output_item_id
        k = body.output_qty / (recipe.output_qty or 1.0)
        required = []
        for it in (
            db.query(RecipeItem)
            .filter(RecipeItem.recipe_id == recipe.id)
            .order_by(RecipeItem.sort_order)
            .all()
        ):
            required.append({"item_id": it.item_id, "qty": float(it.qty_required) * k, "is_optional": bool(it.is_optional)})
    else:
        if not body.output_item_id:
            raise HTTPException(status_code=400, detail="output_item_id required for ad-hoc run")
        output_item_id = body.output_item_id
        k = 1.0
        if not body.components:
            raise HTTPException(status_code=400, detail="components required for ad-hoc run")
        required = [
            {"item_id": c.item_id, "qty": c.qty_required, "is_optional": False}
            for c in body.components
        ]

    run = ManufacturingRun(
        recipe_id=body.recipe_id,
        output_item_id=output_item_id,
        output_qty=body.output_qty,
        status="created",
        notes=body.notes,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    shortages = []
    for r in required:
        if r["is_optional"]:
            continue
        on_hand = on_hand_qty(db, r["item_id"])
        if on_hand + 1e-9 < r["qty"]:
            shortages.append(
                {
                    "item_id": r["item_id"],
                    "required": r["qty"],
                    "on_hand": on_hand,
                    "missing": r["qty"] - on_hand,
                }
            )
    if shortages:
        run.status = "failed_insufficient_stock"
        run.meta = json.dumps({"shortages": shortages})
        db.commit()
        raise HTTPException(status_code=400, detail={"status": "failed_insufficient_stock", "shortages": shortages})

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
        run = db.get(ManufacturingRun, run.id)
        if run:
            run.status = "failed_insufficient_stock"
            run.meta = json.dumps({"shortages": exc.shortages})
            db.commit()
        raise HTTPException(status_code=400, detail={"status": "failed_insufficient_stock", "shortages": exc.shortages})
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        run = db.get(ManufacturingRun, run.id)
        if run:
            run.status = "failed_error"
            run.meta = json.dumps({"error": str(exc)[:500]})
            db.commit()
        raise HTTPException(status_code=500, detail={"status": "failed_error"})
