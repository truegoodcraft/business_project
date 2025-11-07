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

"""Approval helpers for gating state-changing operations."""

from __future__ import annotations

import os
from typing import Optional
from uuid import uuid4

from core import policy_log
from core.action_cards.model import ActionCard
from core.unilog import write as uni_write


def _auto_approve_enabled() -> bool:
    """Return True when AUTO_APPROVE flag enables auto approvals."""

    value = os.getenv("AUTO_APPROVE", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def request_approval(card: ActionCard) -> Optional[str]:
    """Request approval for the provided action card."""

    uni_write("approvals.request", None, card_id=card.id, kind=card.kind)
    token = f"approval-{uuid4()}"
    if _auto_approve_enabled():
        card.state = "approved"
        uni_write("approvals.granted", None, card_id=card.id, token=token)
        record_approval(token, card.id)
        return token

    answer = input(f"Approve action card {card.title}? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        uni_write("approvals.denied", None, card_id=card.id)
        return None

    card.state = "approved"
    uni_write("approvals.granted", None, card_id=card.id, token=token)
    record_approval(token, card.id)
    return token


def record_approval(op_id: str, card_id: str, *, user: str = "local") -> None:
    """Record an approval decision to the policy log."""

    decision = {
        "run_id": None,
        "card_id": card_id,
        "op_id": op_id,
        "user": user,
        "approved": True,
    }
    policy_log.log_policy(f"card:{card_id}", decision)


def can_apply(card: ActionCard) -> bool:
    """Return True if the card may proceed to apply."""

    return card.state in {"approved", "applied"}
