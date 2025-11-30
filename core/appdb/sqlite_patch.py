# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

"""SQLite-safe, idempotent schema patches for the vendors table."""

from typing import Set

from sqlalchemy.engine import Engine


def _vendor_columns(conn) -> Set[str]:
    cols = set()
    for row in conn.exec_driver_sql("PRAGMA table_info('vendors')"):
        # row: (cid, name, type, notnull, dflt_value, pk)
        cols.add(row[1])
    return cols


def ensure_vendors_schema(engine: Engine) -> None:
    """Ensure vendors table has columns expected by Contacts features.

    Adds missing columns using SQLite-safe ALTER TABLE statements and creates
    indexes for commonly filtered boolean flags. Safe to run multiple times.
    """

    with engine.begin() as conn:
        cols = _vendor_columns(conn)

        def _add(col: str, ddl: str) -> None:
            nonlocal cols
            if col not in cols:
                conn.exec_driver_sql(f"ALTER TABLE vendors ADD COLUMN {ddl}")
                cols.add(col)

        _add("is_vendor", "is_vendor INTEGER NOT NULL DEFAULT 0")
        _add("is_org", "is_org INTEGER NOT NULL DEFAULT 0")
        _add("role", "role TEXT DEFAULT 'contact'")
        _add("contact", "contact TEXT")
        _add("organization_id", "organization_id INTEGER")
        _add("meta", "meta TEXT")

        # Backfill sensible defaults
        conn.exec_driver_sql(
            "UPDATE vendors SET role='contact' WHERE role IS NULL OR trim(role)=''"
        )
        # Align flag columns with any legacy role/kind values
        conn.exec_driver_sql(
            """
            UPDATE vendors
            SET is_vendor = CASE lower(coalesce(role, ''))
                WHEN 'vendor' THEN 1
                WHEN 'both' THEN 1
                ELSE coalesce(is_vendor, 0)
            END
            """
        )
        if "kind" in cols:
            conn.exec_driver_sql(
                """
                UPDATE vendors
                SET is_org = CASE lower(coalesce(kind, ''))
                    WHEN 'org' THEN 1
                    ELSE coalesce(is_org, 0)
                END
                """
            )
        else:
            conn.exec_driver_sql("UPDATE vendors SET is_org = coalesce(is_org, 0)")

        conn.exec_driver_sql(
            "UPDATE vendors SET meta='{}' WHERE meta IS NULL OR trim(meta)=''"
        )

        # Helpful indexes for boolean filters
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS vendors_is_vendor_idx ON vendors(is_vendor)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS vendors_is_org_idx ON vendors(is_org)"
        )


__all__ = ["ensure_vendors_schema"]
