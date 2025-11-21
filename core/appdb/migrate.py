# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .paths import app_db_path


def _legacy_repo_db() -> Path:
    """
    Legacy location (pre-cutover): app.db at the repo working directory.
    In dev, BUS_ROOT points at the repo root; otherwise fall back to CWD.
    """
    base = Path(os.environ.get("BUS_ROOT") or Path.cwd())
    return base / "app.db"


def ensure_appdb_migrated() -> None:
    """
    Idempotent copy-once migration:
      - If new AppData DB is missing and legacy repo DB exists, copy legacy -> new.
      - If both exist, prefer the new AppData DB (do nothing).
      - If neither exists, do nothing; the engine will create a fresh DB at the new location.
    Never remove or overwrite any existing DB file.
    """
    new_db = app_db_path()
    old_db = _legacy_repo_db()

    try:
        if new_db.exists():
            return  # already migrated or freshly created

        if not old_db.exists():
            return  # nothing to migrate

        new_db.parent.mkdir(parents=True, exist_ok=True)

        # Copy main file and SQLite sidecars (WAL/SHM) if present.
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(old_db) + suffix)
            dst = Path(str(new_db) + suffix)
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
    except Exception:
        # Fail-closed on migration error: do not block startup.
        # Engine will create a fresh DB at the new path if needed.
        pass


__all__ = ["ensure_appdb_migrated"]

