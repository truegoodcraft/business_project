# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.services.models import Item, Recipe, RecipeItem
from core.journal.manufacturing import append_journal
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])

MAX_INT64 = 2**63 - 1


class RunDTO(BaseModel):
    recipe_id: int = Field(...)
    multiplier: int = Field(1, ge=1)


def _guard_int_bounds(value: int):
    if abs(value) > MAX_INT64:
        raise HTTPException(status_code=400, detail="quantity overflow: exceeds 64-bit integer")


@router.post("/run")
async def run_recipe(
    payload: RunDTO,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = db.query(Recipe).get(payload.recipe_id)
    if not r:
        raise HTTPException(404, "recipe not found")
    deltas: dict[int, int] = {}
    for ri in db.query(RecipeItem).filter_by(recipe_id=r.id).all():
        sign = -1 if ri.role == 'input' else 1
        delta = sign * (ri.qty_stored * payload.multiplier)
        _guard_int_bounds(delta)
        deltas[ri.item_id] = deltas.get(ri.item_id, 0) + delta
    for iid, d in deltas.items():
        _guard_int_bounds(d)
        it = db.query(Item).get(iid)
        if not it:
            raise HTTPException(400, detail=f"item {iid} missing")
        next_qty = (it.qty_stored or 0) + d
        _guard_int_bounds(next_qty)
        it.qty_stored = next_qty
    db.commit()
    append_journal(r, payload.multiplier, deltas)
    return { 'ok': True, 'applied': deltas }
