# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from core.appdb.paths import app_db_path


def ensure_appdb_migrated() -> None:
    """No-op migration placeholder; ensures AppData path exists."""
    app_db_path()


__all__ = ["ensure_appdb_migrated"]
