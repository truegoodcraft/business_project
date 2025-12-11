# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional

from pydantic import BaseModel


class StockInReq(BaseModel):
    item_id: int
    uom: str
    quantity_decimal: str
    unit_cost_decimal: Optional[str] = None
    vendor_id: Optional[int] = None
    notes: Optional[str] = None


class QtyDisplay(BaseModel):
    unit: str
    value: str


class StockInResp(BaseModel):
    batch_id: int
    qty_added_int: int
    stock_on_hand_int: int
    stock_on_hand_display: QtyDisplay
    fifo_unit_cost_display: Optional[str] = None
