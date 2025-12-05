# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/transactions/summary")
def transactions_summary(window: str = Query("30d")):
    """
    STUB: Replace when transactions module lands.
    Returns the shape expected by the UI while clearly marked as a stub.
    """

    return {
        "stub": True,
        "window": window,
        "as_of": datetime.utcnow().isoformat(),
        "totals": {"count": 0, "in": 0, "out": 0},
    }


@router.get("/transactions")
def transactions_list(limit: int = 10):
    """STUB: Empty transaction listing placeholder."""

    return {
        "stub": True,
        "limit": limit,
        "items": [],
    }
