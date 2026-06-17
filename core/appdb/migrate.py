# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from core.appdb.paths import app_db_path
from core.appdb.sqlite_patch import ensure_vendors_schema


def ensure_appdb_migrated() -> None:
    """No-op migration placeholder; ensures AppData path exists."""
    app_db_path()


def ensure_vendors_flags(engine: Engine) -> None:
    """Ensure required vendor columns exist (idempotent)."""

    ensure_vendors_schema(engine)


def ensure_invoice_bootstrap(engine: Engine) -> None:
    """Ensure invoice sequence seed and invoice-scoped indexes exist."""

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO document_sequences(key, next_number)
                SELECT 'invoice', 1001
                WHERE NOT EXISTS (
                    SELECT 1 FROM document_sequences WHERE key='invoice'
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoices_invoice_number ON invoices(invoice_number)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoice_lines_invoice_sort ON invoice_lines(invoice_id, sort_order, id)"))
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_cash_events_invoice_source
                ON cash_events(source_kind, source_id)
                WHERE source_kind='invoice'
                """
            )
        )


__all__ = ["ensure_appdb_migrated", "ensure_vendors_flags", "ensure_invoice_bootstrap"]
