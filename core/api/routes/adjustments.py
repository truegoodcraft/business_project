# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.appdb.ledger import add_batch, fifo_consume, on_hand_qty
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/ledger", tags=["ledger"])


class AdjustmentInput(BaseModel):
    item_id: int
    qty_change: float = Field(..., ne=0)
    note: str | None = None


@router.post("/adjust")
async def adjust_stock(
    body: AdjustmentInput,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    if body.qty_change > 0:
        add_batch(
            db,
            body.item_id,
            body.qty_change,
            unit_cost_cents=0,
            source_kind="adjustment",
            source_id=None,
        )
        db.commit()
        return {"ok": True}

    need = abs(body.qty_change)
    on_hand = on_hand_qty(db, body.item_id)
    if on_hand + 1e-9 < need:
        raise HTTPException(status_code=400, detail="insufficient stock for negative adjustment")
    fifo_consume(db, body.item_id, need, source_kind="adjustment", source_id=None)
    db.commit()
    return {"ok": True}
