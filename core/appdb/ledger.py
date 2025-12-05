# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import List, Optional

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session

from core.appdb.models import Item, ItemBatch, ItemMovement


def on_hand_qty(session: Session, item_id: int) -> float:
    return float(
        session.execute(
            select(func.coalesce(func.sum(ItemBatch.qty_remaining), 0.0)).where(ItemBatch.item_id == item_id)
        ).scalar_one()
    )


class InsufficientStock(Exception):
    def __init__(self, shortages: list[dict]):
        super().__init__("insufficient_stock")
        self.shortages = shortages


def fifo_consume(
    session: Session, item_id: int, qty_needed: float, source_kind: str, source_id: Optional[int]
) -> List[ItemMovement]:
    if qty_needed <= 0:
        return []

    avail = on_hand_qty(session, item_id)
    if avail + 1e-9 < qty_needed:
        raise InsufficientStock(
            [
                {
                    "item_id": item_id,
                    "required": qty_needed,
                    "on_hand": avail,
                    "missing": qty_needed - avail,
                }
            ]
        )

    batches = (
        session.execute(
            select(ItemBatch)
            .where(ItemBatch.item_id == item_id, ItemBatch.qty_remaining > 1e-12)
            .order_by(asc(ItemBatch.created_at), asc(ItemBatch.id))
        )
        .scalars()
        .all()
    )

    moves: List[ItemMovement] = []
    remaining = qty_needed
    for batch in batches:
        if remaining <= 1e-9:
            break
        take = min(batch.qty_remaining, remaining)
        batch.qty_remaining -= take
        remaining -= take
        mv = ItemMovement(
            item_id=item_id,
            batch_id=batch.id,
            qty_change=-take,
            unit_cost_cents=batch.unit_cost_cents,
            source_kind=source_kind,
            source_id=source_id,
            is_oversold=False,
        )
        session.add(mv)
        moves.append(mv)

    if remaining > 1e-9:
        raise InsufficientStock(
            [
                {
                    "item_id": item_id,
                    "required": qty_needed,
                    "on_hand": avail,
                    "missing": remaining,
                }
            ]
        )
    item = session.get(Item, item_id)
    if item:
        item.qty_stored = (item.qty_stored or 0) - qty_needed
    return moves


def add_batch(
    session: Session,
    item_id: int,
    qty: float,
    unit_cost_cents: int,
    source_kind: str,
    source_id: Optional[int],
): 
    if qty <= 0:
        return None
    batch = ItemBatch(
        item_id=item_id,
        qty_initial=qty,
        qty_remaining=qty,
        unit_cost_cents=unit_cost_cents,
        source_kind=source_kind,
        source_id=source_id,
        is_oversold=False,
    )
    session.add(batch)
    session.flush()
    mv = ItemMovement(
        item_id=item_id,
        batch_id=batch.id,
        qty_change=qty,
        unit_cost_cents=unit_cost_cents,
        source_kind=source_kind,
        source_id=source_id,
        is_oversold=False,
    )
    session.add(mv)
    item = session.get(Item, item_id)
    if item:
        item.qty_stored = (item.qty_stored or 0) + qty
    return batch.id
