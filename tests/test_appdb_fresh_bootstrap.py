# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from sqlalchemy import text


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
