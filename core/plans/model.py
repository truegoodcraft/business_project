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

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionKind(str, Enum):
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    RENAME = "rename"
    HARDLINK = "hardlink"


class Action(BaseModel):
    id: str
    kind: ActionKind
    # For now we allow absolute paths via meta (will switch to opaque IDs later):
    # meta.src_path, meta.dst_parent_path, meta.dst_name, meta.dst_path
    src_id: Optional[str] = None
    dst_parent_id: Optional[str] = None
    dst_name: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class PlanStatus(str, Enum):
    DRAFT = "draft"
    PREVIEWED = "previewed"
    COMMITTED = "committed"
    FAILED = "failed"


class Plan(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str  # e.g., "ui" or "plugin:organizer@1.0.0"
    title: str
    note: Optional[str] = None
    actions: List[Action]
    status: PlanStatus = PlanStatus.DRAFT
    stats: Dict[str, Any] = Field(default_factory=dict)
