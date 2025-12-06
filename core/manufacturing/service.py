# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared manufacturing service utilities."""

from __future__ import annotations

import json
from contextlib import wraps
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.api.schemas.manufacturing import (
    AdhocRunRequest,
    ManufacturingRunRequest,
    RecipeRunRequest,
)
from core.appdb.ledger import InsufficientStock, on_hand_qty
from core.appdb.models import Item, ItemBatch, ItemMovement
from core.appdb.models_recipes import Recipe, RecipeItem
from core.journal.manufacturing import PATH as MANUFACTURING_JOURNAL_PATH


def transactional(func: Callable):
    @wraps(func)
    def wrapper(session: Session, *args, **kwargs):
        on_before_commit = kwargs.pop("on_before_commit", None)
        try:
            result = func(session, *args, **kwargs)
            if on_before_commit:
                on_before_commit(result)
            session.commit()
            return result
        except HTTPException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise

    return wrapper


class fifo:
    @staticmethod
    def allocate(session: Session, item_id: int, qty: float) -> List[dict]:
        if qty <= 0:
            return []

        batches = (
            session.query(ItemBatch)
            .filter(ItemBatch.item_id == item_id, ItemBatch.qty_remaining > 1e-12)
            .order_by(ItemBatch.created_at, ItemBatch.id)
            .with_for_update()
            .all()
        )
        available = sum(float(b.qty_remaining) for b in batches)
        if available + 1e-9 < qty:
            raise InsufficientStock(
                [
                    {
                        "item_id": item_id,
                        "required": qty,
                        "on_hand": available,
                        "missing": qty - available,
                    }
                ]
            )

        allocations: List[dict] = []
        remaining = qty
        for batch in batches:
            if remaining <= 1e-9:
                break
            take = min(float(batch.qty_remaining), remaining)
            if take <= 0:
                continue
            batch.qty_remaining = float(batch.qty_remaining) - take
            remaining -= take
            allocations.append(
                {
                    "item_id": item_id,
                    "batch_id": batch.id,
                    "qty": take,
                    "unit_cost_cents": batch.unit_cost_cents,
                }
            )

        return allocations


def append_run_journal(entry: dict) -> None:
    Path(MANUFACTURING_JOURNAL_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(MANUFACTURING_JOURNAL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


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


@transactional
def execute_run_txn(
    session: Session,
    body: ManufacturingRunRequest,
    output_item_id: int,
    required: list[dict],
    k: float,
):
    from core.appdb.models_recipes import ManufacturingRun

    mfg_run = ManufacturingRun(
        recipe_id=getattr(body, "recipe_id", None),
        output_item_id=output_item_id,
        output_qty=body.output_qty,
        status="created",
        notes=getattr(body, "notes", None),
    )
    session.add(mfg_run)
    session.flush()

    allocations: List[dict] = []
    cost_inputs_cents = 0
    consumed_per_item: dict[int, float] = {}
    for r in required:
        if r["qty"] <= 0:
            continue
        if r["is_optional"]:
            if on_hand_qty(session, r["item_id"]) + 1e-9 < r["qty"]:
                continue
        slices = fifo.allocate(session, r["item_id"], r["qty"])
        for alloc in slices:
            allocations.append(alloc)
            consumed_per_item[alloc["item_id"]] = consumed_per_item.get(alloc["item_id"], 0) + alloc[
                "qty"
            ]
            if alloc["unit_cost_cents"] is not None:
                cost_inputs_cents += int(round(alloc["unit_cost_cents"] * alloc["qty"]))

    for alloc in allocations:
        session.add(
            ItemMovement(
                item_id=alloc["item_id"],
                batch_id=alloc["batch_id"],
                qty_change=-alloc["qty"],
                unit_cost_cents=alloc["unit_cost_cents"],
                source_kind="manufacturing",
                source_id=mfg_run.id,
                is_oversold=False,
            )
        )

    per_output_cents = int(round(cost_inputs_cents / max(body.output_qty, 1e-9)))
    output_batch = ItemBatch(
        item_id=output_item_id,
        qty_initial=body.output_qty,
        qty_remaining=body.output_qty,
        unit_cost_cents=per_output_cents,
        source_kind="manufacturing",
        source_id=mfg_run.id,
        is_oversold=False,
    )
    session.add(output_batch)
    session.flush()

    session.add(
        ItemMovement(
            item_id=output_item_id,
            batch_id=output_batch.id,
            qty_change=body.output_qty,
            unit_cost_cents=per_output_cents,
            source_kind="manufacturing",
            source_id=mfg_run.id,
            is_oversold=False,
        )
    )

    for item_id, qty in consumed_per_item.items():
        item = session.get(Item, item_id)
        if item:
            item.qty_stored = (item.qty_stored or 0) - qty

    output_item = session.get(Item, output_item_id)
    if output_item:
        output_item.qty_stored = (output_item.qty_stored or 0) + body.output_qty

    mfg_run.status = "completed"
    mfg_run.executed_at = datetime.utcnow()
    mfg_run.meta = json.dumps(
        {
            "k": k,
            "cost_inputs_cents": cost_inputs_cents,
            "per_output_cents": per_output_cents,
            "allocations": allocations,
            "output_batch_id": output_batch.id,
        }
    )

    journal_entry = {
        "run_id": mfg_run.id,
        "recipe_id": getattr(body, "recipe_id", None),
        "output_item_id": output_item_id,
        "output_qty": body.output_qty,
        "allocations": allocations,
        "output_batch_id": output_batch.id,
        "per_output_cents": per_output_cents,
        "cost_inputs_cents": cost_inputs_cents,
    }

    return {"run": mfg_run, "journal_entry": journal_entry}


__all__ = ["append_run_journal", "execute_run_txn", "fifo", "format_shortages", "validate_run"]
