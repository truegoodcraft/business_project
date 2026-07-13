# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest


def test_fresh_database_bootstrap_creates_invoice_sequence(bus_client):
    engine_module = bus_client["engine"]
    models = bus_client["models"]
    api_http = bus_client["api_http"]
    engine = engine_module.get_engine()

    models.Base.metadata.drop_all(bind=engine)
    api_http.startup_migrations()

    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        next_number = connection.execute(
            text("SELECT next_number FROM document_sequences WHERE key='invoice'")
        ).scalar_one()

    assert {"document_sequences", "invoices", "invoice_lines"} <= tables
    assert next_number == 1001
    with engine.connect() as connection:
        indexes = {
            row[1]
            for row in connection.execute(text("PRAGMA index_list('invoices')"))
        }
    assert "ux_invoices_active_job" in indexes


def test_invoice_bootstrap_reconciles_duplicate_active_job_links(bus_client):
    engine_module = bus_client["engine"]
    models = bus_client["models"]
    api_http = bus_client["api_http"]
    engine = engine_module.get_engine()

    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ux_invoices_active_job"))
    with engine_module.SessionLocal() as db:
        contact = models.Vendor(name="Migration Contact", role="contact", is_vendor=0)
        db.add(contact)
        db.flush()
        job = models.Job(title="Migration Job", contact_id=int(contact.id), status="draft")
        db.add(job)
        db.flush()
        db.add_all(
            [
                models.Invoice(invoice_number="INV-MIG-1", contact_id=contact.id, job_id=job.id, status="draft"),
                models.Invoice(invoice_number="INV-MIG-2", contact_id=contact.id, job_id=job.id, status="paid"),
            ]
        )
        db.commit()
        job_id = int(job.id)
        contact_id = int(contact.id)

    api_http.startup_migrations()

    with engine_module.SessionLocal() as db:
        invoices = db.query(models.Invoice).filter(
            models.Invoice.invoice_number.in_(["INV-MIG-1", "INV-MIG-2"])
        ).order_by(models.Invoice.invoice_number).all()
        assert len(invoices) == 2
        assert sum(invoice.job_id == job_id for invoice in invoices) == 1
        assert next(invoice for invoice in invoices if invoice.job_id == job_id).status == "paid"
        db.add(
            models.Invoice(
                invoice_number="INV-MIG-3",
                contact_id=contact_id,
                job_id=job_id,
                status="draft",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
