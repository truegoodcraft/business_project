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
        # Older working revisions allowed more than one non-void invoice to
        # retain the same job link. Preserve every invoice and its financial
        # state, but keep only the most authoritative link (paid, then issued,
        # then draft; oldest id breaks ties) before installing the invariant.
        active_links = conn.execute(
            text(
                """
                SELECT id, job_id, status
                FROM invoices
                WHERE job_id IS NOT NULL AND status <> 'void'
                ORDER BY job_id,
                         CASE status
                           WHEN 'paid' THEN 0
                           WHEN 'issued' THEN 1
                           ELSE 2
                         END,
                         id
                """
            )
        ).mappings().all()
        claimed_job_ids: set[int] = set()
        for row in active_links:
            job_id = int(row["job_id"])
            if job_id not in claimed_job_ids:
                claimed_job_ids.add(job_id)
                continue
            conn.execute(
                text("UPDATE invoices SET job_id = NULL WHERE id = :invoice_id"),
                {"invoice_id": int(row["id"])},
            )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_invoices_active_job
                ON invoices(job_id)
                WHERE job_id IS NOT NULL AND status <> 'void'
                """
            )
        )
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
