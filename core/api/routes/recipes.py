# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from core.services.models import Item, Recipe, RecipeItem
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/recipes", tags=["recipes"])


class RecipeItemDTO(BaseModel):
    id: int
    item_id: int
    role: Literal["input", "output"]
    qty_stored: int

    class ItemMini(BaseModel):
        id: int
        name: str
        uom: str
        qty_stored: int

    item: ItemMini


class RecipeDTO(BaseModel):
    id: int
    name: str
    notes: str | None = None
    items: List[RecipeItemDTO] = []


@router.get("")
async def list_recipes(
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    rs = db.query(Recipe).all()
    out = []
    for r in rs:
        out.append({
            "id": r.id,
            "name": r.name,
            "notes": r.notes,
        })
    return out


@router.get("/{rid}")
async def get_recipe(
    rid: int,
    db: Session = Depends(get_session),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    r = db.query(Recipe).get(rid)
    if not r:
        raise HTTPException(404, "recipe not found")
    items = []
    for ri in r.items:
        it = db.query(Item).get(ri.item_id)
        items.append({
            "id": ri.id,
            "item_id": ri.item_id,
            "role": ri.role,
            "qty_stored": ri.qty_stored,
            "item": {
                "id": it.id,
                "name": it.name,
                "uom": it.uom,
                "qty_stored": it.qty_stored,
            },
        })
    return {"id": r.id, "name": r.name, "notes": r.notes, "items": items}


class UpsertRecipeDTO(BaseModel):
    name: str
    notes: str | None = None
    items: List[dict] = []  # {item_id, role, qty_stored}


@router.post("")
async def create_recipe(
    payload: UpsertRecipeDTO,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = Recipe(name=payload.name, notes=payload.notes)
    db.add(r)
    db.flush()
    for it in payload.items:
        db.add(
            RecipeItem(
                recipe_id=r.id,
                item_id=it["item_id"],
                role=it["role"],
                qty_stored=it["qty_stored"],
            )
        )
    db.commit()
    return {"id": r.id}


@router.put("/{rid}")
async def update_recipe(
    rid: int,
    payload: UpsertRecipeDTO,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    r = db.query(Recipe).get(rid)
    if not r:
        raise HTTPException(404, "recipe not found")
    r.name = payload.name
    r.notes = payload.notes
    db.query(RecipeItem).filter(RecipeItem.recipe_id == rid).delete()
    for it in payload.items:
        db.add(
            RecipeItem(
                recipe_id=rid,
                item_id=it["item_id"],
                role=it["role"],
                qty_stored=it["qty_stored"],
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
    r = db.query(Recipe).get(rid)
    if not r:
        return {"ok": True}
    db.delete(r)
    db.commit()
    return {"ok": True}
