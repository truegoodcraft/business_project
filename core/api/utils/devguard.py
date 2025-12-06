"""Development-only guard helpers."""
import os
from fastapi import HTTPException

def is_dev() -> bool:
    """
    Central check for 'dev mode'.
    Strict: only BUS_DEV == "1" enables dev.
    """
    return os.getenv("BUS_DEV", "0") == "1"

def require_dev() -> None:
    """Return 404 when BUS_DEV is not enabled to avoid advertising dev routes."""
    if not is_dev():
        raise HTTPException(status_code=404, detail="Not found")
