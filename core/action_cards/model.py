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

"""Action card models shared between the core and plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DiffEntry:
    """Describe a change that an action card proposes."""

    path: str
    before: Any
    after: Any

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise ValueError("DiffEntry.path must be a non-empty string")


@dataclass
class ActionCard:
    """Plan-time representation of a unit of work."""

    id: str
    kind: str
    title: str
    summary: str
    proposed_by_plugin: str
    data: Dict[str, Any] = field(default_factory=dict)
    diff: List[DiffEntry] = field(default_factory=list)
    risk: str = "low"
    prerequisites: List[str] = field(default_factory=list)
    approvals_required: int = 1
    state: str = "proposed"

    def __post_init__(self) -> None:
        for attr in ("id", "kind", "title", "summary", "proposed_by_plugin", "risk"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{attr} must be a non-empty string")
        if not isinstance(self.data, dict):
            raise TypeError("data must be a dictionary")
        if not isinstance(self.diff, list):
            raise TypeError("diff must be a list of DiffEntry items")
        for entry in self.diff:
            if not isinstance(entry, DiffEntry):
                raise TypeError("diff entries must be DiffEntry instances")
        if not isinstance(self.prerequisites, list):
            raise TypeError("prerequisites must be a list of card IDs")
        for item in self.prerequisites:
            if not isinstance(item, str):
                raise TypeError("prerequisite values must be strings")
        if not isinstance(self.approvals_required, int) or self.approvals_required < 1:
            raise ValueError("approvals_required must be a positive integer")
        if self.state not in {"proposed", "approved", "applied", "failed"}:
            raise ValueError("state must be one of proposed, approved, applied, failed")
