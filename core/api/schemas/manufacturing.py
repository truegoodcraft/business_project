"""
Pydantic schemas and helpers for manufacturing runs.
"""
from __future__ import annotations

from typing import Any, List, Union

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError


class ComponentInput(BaseModel):
    item_id: int
    qty_required: float = Field(..., gt=0)
    is_optional: bool = False


class RecipeRunRequest(BaseModel):
    recipe_id: int = Field(..., gt=0)
    output_qty: float = Field(..., gt=0)
    notes: str | None = None


class AdhocRunRequest(BaseModel):
    output_item_id: int = Field(..., gt=0)
    output_qty: float = Field(..., gt=0)
    components: List[ComponentInput] = Field(..., min_length=1)
    notes: str | None = None


ManufacturingRunRequest = Union[RecipeRunRequest, AdhocRunRequest]


def parse_run_request(payload: Any) -> ManufacturingRunRequest:
    if isinstance(payload, list):
        raise HTTPException(status_code=400, detail="single run only")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    has_recipe = payload.get("recipe_id") is not None
    has_output_item = payload.get("output_item_id") is not None
    has_components = payload.get("components") is not None

    if has_recipe and (has_output_item or has_components):
        raise HTTPException(status_code=400, detail="recipe and ad-hoc payloads are mutually exclusive")

    try:
        if has_recipe:
            return RecipeRunRequest(**payload)
        if has_output_item or has_components:
            if not payload.get("components"):
                raise HTTPException(status_code=400, detail="components required for ad-hoc run")
            return AdhocRunRequest(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())

    raise HTTPException(status_code=400, detail="recipe_id or output_item_id required")


__all__ = [
    "AdhocRunRequest",
    "ComponentInput",
    "ManufacturingRunRequest",
    "RecipeRunRequest",
    "parse_run_request",
]
