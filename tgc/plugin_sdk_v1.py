# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plugin SDK version 1.0 exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, runtime_checkable

from core.action_cards.model import ActionCard as CoreActionCard
from core.bus.models import ApplyResult as CoreApplyResult


ActionCard = CoreActionCard
ApplyResult = CoreApplyResult


@dataclass
class ApplyRequest:
    """Structured payload passed to plugin apply handlers."""

    ctx: Dict[str, object]
    card: ActionCard
    metadata: Dict[str, object] = field(default_factory=dict)


@runtime_checkable
class PluginV1(Protocol):
    """Interface for plugins targeting SDK version 1.0."""

    api_version: str

    def propose(self, ctx: Dict[str, object], input: Dict[str, object]) -> List[ActionCard]:
        ...

    def apply(self, ctx: Dict[str, object], card: ActionCard) -> Dict[str, object]:
        ...

    def rollback(self, ctx: Dict[str, object], op_snapshot: Dict[str, object]) -> Dict[str, object]:
        ...

    def health(self) -> Dict[str, object]:
        ...


__all__ = [
    "ActionCard",
    "ApplyRequest",
    "ApplyResult",
    "PluginV1",
]
