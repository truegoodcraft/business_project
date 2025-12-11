# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.appdb.engine import get_session
from core.appdb.models import Item
from core.appdb.models_recipes import ManufacturingRun, Recipe, RecipeItem
from core.config.writes import require_writes
from core.policy.guard import require_owner_commit
from tgc.security import require_token_ctx
from tgc.state import AppState, get_state

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _journals_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        # Linux/macOS fallback
        root = os.path.expanduser("~/.local/share")
    d = Path(root) / "BUSCore" / "app" / "data" / "journals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _append_recipe_journal(entry: dict) -> None:
    try:
        entry = dict(entry)
        entry.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
        p = _journals_dir() / "recipes.jsonl"
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except Exception:
        pass


class RecipeItemIn(BaseModel):
    item_id: int
    qty_required: int
    optional: bool = False
    sort: int = 0


class RecipeCreate(BaseModel):
    name: str
    code: str | None = None
    output_item_id: int
    output_qty: int = 1
    archived: bool = False
    notes: str | None = None
    items: list[RecipeItemIn] = []


class RecipeUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    output_item_id: int | None = None
    output_qty: int | None = None
    archived: bool | None = None
    notes: str | None = None
    items: list[RecipeItemIn] = []


def _serialize_recipe_detail(db: Session, recipe: Recipe) -> dict:
    items = []
    for ri in (
        db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).order_by(RecipeItem.sort_order).all()
    ):
        it = db.get(Item, ri.item_id)
        items.append(
            {
                "id": ri.id,
                "item_id": ri.item_id,
                "qty_required": ri.qty_required,
                "optional": bool(ri.is_optional),
                "sort": ri.sort_order,
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

    output_item = db.get(Item, recipe.output_item_id) if recipe.output_item_id else None
    return {
        "id": recipe.id,
        "name": recipe.name,
        "code": recipe.code,
        "output_item_id": recipe.output_item_id,
        "output_qty": recipe.output_qty,
        "archived": bool(recipe.archived),
        "notes": recipe.notes,
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
            "archived": bool(r.archived),
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
    return _serialize_recipe_detail(db, r)


@router.post("")
async def create_recipe(
    payload: RecipeCreate,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    recipe = Recipe(
        name=payload.name,
        code=payload.code,
        output_item_id=payload.output_item_id,
        output_qty=1,
        archived=bool(payload.archived),
        notes=payload.notes,
    )
    db.add(recipe)
    db.flush()
    for idx, it in enumerate(payload.items or []):
        if it.qty_required <= 0:
            raise HTTPException(status_code=400, detail="qty_required must be > 0")
        db.add(
            RecipeItem(
                recipe_id=recipe.id,
                item_id=it.item_id,
                qty_required=it.qty_required,
                is_optional=it.optional,
                sort_order=it.sort or idx,
            )
        )
    db.commit()
    db.refresh(recipe)
    _append_recipe_journal({
        "type": "recipe.create",
        "recipe_id": int(recipe.id),
        "recipe_name": recipe.name,
    })
    return _serialize_recipe_detail(db, recipe)


@router.put("/{rid}")
async def update_recipe(
    rid: int,
    payload: RecipeUpdate,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
):
    require_owner_commit(req)
    recipe = db.get(Recipe, rid)
    if not recipe:
        raise HTTPException(404, "recipe not found")
    if payload.name is not None:
        recipe.name = payload.name
    if payload.code is not None:
        recipe.code = payload.code
    if payload.output_item_id is not None:
        recipe.output_item_id = payload.output_item_id
    recipe.output_qty = 1
    if payload.archived is not None:
        recipe.archived = bool(payload.archived)
    if payload.notes is not None:
        recipe.notes = payload.notes
    db.query(RecipeItem).filter(RecipeItem.recipe_id == rid).delete()
    for idx, it in enumerate(payload.items or []):
        if it.qty_required <= 0:
            raise HTTPException(status_code=400, detail="qty_required must be > 0")
        db.add(
            RecipeItem(
                recipe_id=rid,
                item_id=it.item_id,
                qty_required=it.qty_required,
                is_optional=it.optional,
                sort_order=it.sort or idx,
            )
        )
    db.commit()
    db.refresh(recipe)
    _append_recipe_journal({
        "type": "recipe.update",
        "recipe_id": int(recipe.id),
        "recipe_name": recipe.name,
    })
    return _serialize_recipe_detail(db, recipe)


@router.delete("/{recipe_id}")
async def delete_recipe(
    recipe_id: int,
    req: Request,
    db: Session = Depends(get_session),
    _writes: None = Depends(require_writes),
    _token: str = Depends(require_token_ctx),
    _state: AppState = Depends(get_state),
): 
    require_owner_commit(req)
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(status_code=404, detail="Not Found")
    db.query(ManufacturingRun).filter(ManufacturingRun.recipe_id == recipe_id).update(
        {ManufacturingRun.recipe_id: None}, synchronize_session=False
    )
    db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe_id).delete()
    db.delete(r)
    db.commit()
    _append_recipe_journal(
        {
            "type": "recipe.delete",
            "recipe_id": int(recipe_id),
            "recipe_name": getattr(r, "name", None),
        }
    )
    return {"ok": True, "deleted": recipe_id}
