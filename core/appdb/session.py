# SPDX-License-Identifier: AGPL-3.0-or-later
"""Session helpers for the application database."""

from __future__ import annotations

from typing import Generator

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from core.appdb.engine import SessionLocal, get_session


def get_db(request: Request | None = None) -> Generator[Session, None, None]:
    """Alias for get_session used by FastAPI dependencies."""

    if request is not None and getattr(request.app.state, "maintenance", False):
        raise HTTPException(status_code=503, detail={"error": "maintenance"})

    yield from get_session()


__all__ = ["SessionLocal", "get_db", "get_session"]
