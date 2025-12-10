# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QuantityDisplay(BaseModel):
    unit: str
    value: str


class ItemOut(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    uom: str
    qty_stored: int
    qty: float
    unit: str
    price: Optional[float] = None
    notes: Optional[str] = None
    vendor: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    stock_on_hand_int: int
    stock_on_hand_display: QuantityDisplay

    class Config:
        orm_mode = True


__all__ = ["ItemOut", "QuantityDisplay"]
