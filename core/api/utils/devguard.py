# SPDX-License-Identifier: AGPL-3.0-or-later
"""Development-only guard helpers."""
import os
from fastapi import HTTPException


def require_dev() -> None:
    """Return 404 when BUS_DEV is not enabled to avoid advertising dev routes."""
    if os.getenv("BUS_DEV", "0") != "1":
        raise HTTPException(status_code=404, detail="Not found")
