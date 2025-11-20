# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Inventory contracts used across plugins and the controller core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .common import ID


@dataclass
class InventoryItem:
    """Serializable representation of an inventory item."""

    id: ID
    sku: str
    title: str
    qty: int
    cost: float
    price: float
    vendor_id: Optional[ID]
    drive_file_ids: List[str] = field(default_factory=list)
    notion_page_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, ID):
            raise TypeError("id must be an ID instance")
        if not isinstance(self.sku, str):
            raise TypeError("sku must be a string")
        if not isinstance(self.title, str):
            raise TypeError("title must be a string")
        if not isinstance(self.qty, int):
            raise TypeError("qty must be an int")
        for field_name, value in ("cost", self.cost), ("price", self.price):
            if not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric")
        if self.vendor_id is not None and not isinstance(self.vendor_id, ID):
            raise TypeError("vendor_id must be an ID or None")
        if not isinstance(self.drive_file_ids, list):
            raise TypeError("drive_file_ids must be a list")
        for entry in self.drive_file_ids:
            if not isinstance(entry, str):
                raise TypeError("drive_file_ids entries must be strings")
        if self.notion_page_id is not None and not isinstance(self.notion_page_id, str):
            raise TypeError("notion_page_id must be a string or None")
        for attr in ("created_at", "updated_at"):
            value = getattr(self, attr)
            if value is not None and not isinstance(value, datetime):
                raise TypeError(f"{attr} must be datetime or None")
