# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy.engine import Engine

from core.appdb.paths import app_db_path


def ensure_appdb_migrated() -> None:
    """No-op migration placeholder; ensures AppData path exists."""
    app_db_path()


def ensure_vendors_flags(engine: Engine) -> None:
    """
    Idempotent bootstrap migration:
      - Adds vendors.is_vendor (INTEGER NOT NULL DEFAULT 0) if missing
      - Adds vendors.is_org   (INTEGER NOT NULL DEFAULT 0) if missing
      - Backfills values from legacy columns (role/kind) when present
    Safe for SQLite; no-ops if columns already exist.
    """
    with engine.begin() as conn:
        cols = set()
        for row in conn.exec_driver_sql("PRAGMA table_info('vendors')"):
            # row tuple: (cid, name, type, notnull, dflt_value, pk)
            cols.add(row[1])

        # Add columns if missing
        if "is_vendor" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE vendors ADD COLUMN is_vendor INTEGER NOT NULL DEFAULT 0"
            )
            # Backfill from role if present
            if "role" in cols:
                conn.exec_driver_sql(
                    """
                    UPDATE vendors
                    SET is_vendor = CASE lower(coalesce(role, ''))
                        WHEN 'vendor' THEN 1
                        WHEN 'both'   THEN 1
                        ELSE 0 END
                    """
                )

        if "is_org" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE vendors ADD COLUMN is_org INTEGER NOT NULL DEFAULT 0"
            )
            # Backfill from legacy kind=org if that column still exists
            cols2 = set()
            for row in conn.exec_driver_sql("PRAGMA table_info('vendors')"):
                cols2.add(row[1])
            if "kind" in cols2:
                conn.exec_driver_sql(
                    """
                    UPDATE vendors
                    SET is_org = CASE lower(coalesce(kind, ''))
                        WHEN 'org' THEN 1
                        ELSE 0 END
                    """
                )


__all__ = ["ensure_appdb_migrated", "ensure_vendors_flags"]
