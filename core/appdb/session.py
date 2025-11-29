# SPDX-License-Identifier: AGPL-3.0-or-later
"""Session helpers for the application database."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from core.appdb.engine import SessionLocal, get_session


def get_db() -> Generator[Session, None, None]:
    """Alias for get_session used by FastAPI dependencies."""
    yield from get_session()


__all__ = ["SessionLocal", "get_db", "get_session"]
