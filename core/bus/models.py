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

"""Data models used by the command bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.action_cards.model import ActionCard


@dataclass
class PluginFinding:
    """Discovery output from a plugin."""

    plugin: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    partial: bool = False
    reason: Optional[str] = None

    def count(self) -> int:
        return len(self.records)


@dataclass
class ApplyResult:
    """Result returned from plugin apply hooks."""

    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    ms: int = 0


@dataclass
class RollbackResult:
    """Result returned from plugin rollback hooks."""

    ok: bool
    notes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class HealthStatus:
    """Plugin health status response."""

    ok: Optional[bool]
    notes: List[str] = field(default_factory=list)


@dataclass
class CommandContext:
    """Runtime context passed to bus operations and plugins."""

    controller: Any
    run_id: str
    dry_run: bool
    limits: Any = None
    options: Dict[str, Any] = field(default_factory=dict)
    logger: Any = None
    findings: Dict[str, PluginFinding] = field(default_factory=dict)
    cards: Dict[str, ActionCard] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def get_card(self, card_id: str) -> Optional[ActionCard]:
        return self.cards.get(card_id)
