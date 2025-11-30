# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy.engine import Engine

from core.appdb.paths import app_db_path
from core.appdb.sqlite_patch import ensure_vendors_schema


def ensure_appdb_migrated() -> None:
    """No-op migration placeholder; ensures AppData path exists."""
    app_db_path()


def ensure_vendors_flags(engine: Engine) -> None:
    """Ensure required vendor columns exist (idempotent)."""

    ensure_vendors_schema(engine)


__all__ = ["ensure_appdb_migrated", "ensure_vendors_flags"]
