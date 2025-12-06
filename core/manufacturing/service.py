# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared manufacturing service utilities."""

from __future__ import annotations

from typing import List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import (
    AdhocRunRequest,
    ManufacturingRunRequest,
    RecipeRunRequest,
)
from core.appdb.ledger import on_hand_qty
from core.appdb.models_recipes import Recipe, RecipeItem


def format_shortages(shortages: List[dict]) -> List[dict]:
    formatted = []
    for shortage in shortages:
        formatted.append(
            {
                "item_id": shortage.get("item_id"),
                "required": float(shortage.get("required", 0.0)),
                "available": float(shortage.get("available", shortage.get("on_hand", 0.0))),
            }
        )
    return formatted


def validate_run(session: Session, body: ManufacturingRunRequest) -> Tuple[int, list[dict], float]:
    """Validate a manufacturing run request before any writes occur."""
    if isinstance(body, RecipeRunRequest):
        recipe = session.get(Recipe, body.recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if not recipe.output_item_id:
            raise HTTPException(status_code=400, detail="Recipe has no output_item_id")

        output_item_id = recipe.output_item_id
        k = body.output_qty / (recipe.output_qty or 1.0)
        required = []
        for it in (
            session.query(RecipeItem)
            .filter(RecipeItem.recipe_id == recipe.id)
            .order_by(RecipeItem.sort_order)
            .all()
        ):
            required.append(
                {
                    "item_id": it.item_id,
                    "qty": float(it.qty_required) * k,
                    "is_optional": bool(it.is_optional),
                }
            )
    elif isinstance(body, AdhocRunRequest):
        output_item_id = body.output_item_id
        k = 1.0
        required = [
            {"item_id": c.item_id, "qty": c.qty_required, "is_optional": bool(c.is_optional)}
            for c in body.components
        ]
    else:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="invalid payload")

    shortages: List[dict] = []
    for r in required:
        if r["is_optional"]:
            continue
        on_hand = on_hand_qty(session, r["item_id"])
        if on_hand + 1e-9 < r["qty"]:
            shortages.append({"item_id": r["item_id"], "required": r["qty"], "available": on_hand})

    if shortages:
        raise HTTPException(status_code=400, detail={"shortages": format_shortages(shortages)})

    return output_item_id, required, k


__all__ = ["format_shortages", "validate_run"]
