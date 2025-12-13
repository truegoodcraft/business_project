# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional

from pydantic import BaseModel, StrictStr

try:
    from pydantic import ConfigDict  # v2
    _ModelConfig = ConfigDict
except ImportError:  # pydantic v1 fallback
    _ModelConfig = None  # type: ignore


class StockInReq(BaseModel):
    item_id: int
    uom: StrictStr
    quantity_decimal: StrictStr
    unit_cost_decimal: Optional[StrictStr] = None
    vendor_id: Optional[int] = None
    notes: Optional[StrictStr] = None

    if _ModelConfig:
        model_config = _ModelConfig(extra="forbid")
    else:
        class Config:  # type: ignore
            extra = "forbid"


class QtyDisplay(BaseModel):
    unit: str
    value: str


class StockInResp(BaseModel):
    batch_id: int
    qty_added_int: int
    stock_on_hand_int: int
    stock_on_hand_display: QtyDisplay
    fifo_unit_cost_display: Optional[str] = None
