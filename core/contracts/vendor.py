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

"""Vendor contracts used for inventory coordination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .common import ID


@dataclass
class Vendor:
    """Serializable vendor record."""

    id: ID
    name: str
    email: Optional[str]
    phone: Optional[str]
    drive_folder_id: Optional[str]
    notion_page_id: Optional[str]

    def __post_init__(self) -> None:
        if not isinstance(self.id, ID):
            raise TypeError("id must be an ID instance")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        for attr in ("email", "phone", "drive_folder_id", "notion_page_id"):
            value = getattr(self, attr)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{attr} must be a string or None")
