# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.appdb.models import Item
from core.appdb.models_recipes import Recipe, RecipeItem
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/recipes", tags=["recipes"])


class RecipeItemDTO(BaseModel):
    item_id: int
    qty_required: float = Field(..., gt=0)
    is_optional: bool = False
    sort_order: int = 0


class RecipeDTO(BaseModel):
    id: Optional[int] = None
    name: str
    code: Optional[str] = None
    output_item_id: Optional[int] = None
    output_qty: float = Field(1.0, gt=0)
    is_archived: bool = False
    notes: Optional[str] = None
    items: List[RecipeItemDTO] = []


@router.get("")
async def list_recipes(
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    rs = db.query(Recipe).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "output_item_id": r.output_item_id,
            "output_qty": r.output_qty,
            "is_archived": bool(r.is_archived),
            "notes": r.notes,
        }
        for r in rs
    ]


@router.get("/{rid}")
async def get_recipe(
    rid: int,
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    r = db.get(Recipe, rid)
    if not r:
        raise HTTPException(404, "recipe not found")
    items = []
    for ri in db.query(RecipeItem).filter(RecipeItem.recipe_id == r.id).order_by(RecipeItem.sort_order).all():
        it = db.get(Item, ri.item_id)
        items.append(
            {
                "id": ri.id,
                "item_id": ri.item_id,
                "qty_required": ri.qty_required,
                "is_optional": bool(ri.is_optional),
                "sort_order": ri.sort_order,
                "item": None
                if not it
                else {
                    "id": it.id,
                    "name": it.name,
                    "uom": it.uom,
                    "qty_stored": it.qty_stored,
                },
            }
        )
    output_item = db.get(Item, r.output_item_id) if r.output_item_id else None
    return {
        "id": r.id,
        "name": r.name,
        "code": r.code,
        "output_item_id": r.output_item_id,
        "output_qty": r.output_qty,
        "is_archived": bool(r.is_archived),
        "notes": r.notes,
        "items": items,
        "output_item": None
        if not output_item
        else {
            "id": output_item.id,
            "name": output_item.name,
            "uom": output_item.uom,
            "qty_stored": output_item.qty_stored,
        },
    }


@router.post("")
async def create_recipe(
    payload: RecipeDTO,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = Recipe(
        name=payload.name,
        code=payload.code,
        output_item_id=payload.output_item_id,
        output_qty=payload.output_qty,
        is_archived=payload.is_archived,
        notes=payload.notes,
    )
    db.add(r)
    db.flush()
    for idx, it in enumerate(payload.items or []):
        if it.qty_required <= 0:
            raise HTTPException(status_code=400, detail="qty_required must be > 0")
        db.add(
            RecipeItem(
                recipe_id=r.id,
                item_id=it.item_id,
                qty_required=it.qty_required,
                is_optional=it.is_optional,
                sort_order=it.sort_order or idx,
            )
        )
    db.commit()
    return {"id": r.id}


@router.put("/{rid}")
async def update_recipe(
    rid: int,
    payload: RecipeDTO,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = db.get(Recipe, rid)
    if not r:
        raise HTTPException(404, "recipe not found")
    r.name = payload.name
    r.code = payload.code
    r.output_item_id = payload.output_item_id
    r.output_qty = payload.output_qty
    r.is_archived = payload.is_archived
    r.notes = payload.notes
    db.query(RecipeItem).filter(RecipeItem.recipe_id == rid).delete()
    for idx, it in enumerate(payload.items or []):
        if it.qty_required <= 0:
            raise HTTPException(status_code=400, detail="qty_required must be > 0")
        db.add(
            RecipeItem(
                recipe_id=rid,
                item_id=it.item_id,
                qty_required=it.qty_required,
                is_optional=it.is_optional,
                sort_order=it.sort_order or idx,
            )
        )
    db.commit()
    return {"ok": True}


@router.delete("/{rid}")
async def delete_recipe(
    rid: int,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = db.get(Recipe, rid)
    if not r:
        return {"ok": True}
    db.delete(r)
    db.commit()
    return {"ok": True}
