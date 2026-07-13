# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

pytestmark = pytest.mark.api


def _create_contact(env: dict) -> int:
    with env["engine"].SessionLocal() as db:
        contact = env["models"].Vendor(name="Price Authority Contact", role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def test_job_and_invoice_line_prices_are_finite_nonnegative(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    job_response = client.post(
        "/app/jobs", json={"title": "Price authority job", "contact_id": contact_id}
    )
    assert job_response.status_code == 200, job_response.text
    job_id = int(job_response.json()["id"])

    for invalid in (-1,):
        rejected = client.post(
            f"/app/jobs/{job_id}/lines",
            json={
                "line_type": "service",
                "description": "Invalid job price",
                "quantity_decimal": "1",
                "uom": "ea",
                "unit_price_cents": invalid,
            },
        )
        assert rejected.status_code in {400, 422}

    for literal in ("NaN", "Infinity", "-Infinity"):
        rejected = client.post(
            f"/app/jobs/{job_id}/lines",
            content=(
                '{"line_type":"service","description":"Invalid job price",'
                f'"quantity_decimal":"1","uom":"ea","unit_price_cents":{literal}}}'
            ),
            headers={"Content-Type": "application/json"},
        )
        assert rejected.status_code in {400, 422}

    zero_job_line = client.post(
        f"/app/jobs/{job_id}/lines",
        json={
            "line_type": "service",
            "description": "Valid free work",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 0,
        },
    )
    assert zero_job_line.status_code == 200, zero_job_line.text
    rejected_job_update = client.patch(
        f"/app/jobs/{job_id}/lines/{zero_job_line.json()['id']}",
        json={"unit_price_cents": -10},
    )
    assert rejected_job_update.status_code == 400

    invoice_response = client.post("/app/invoices", json={"contact_id": contact_id})
    assert invoice_response.status_code == 200, invoice_response.text
    invoice_id = int(invoice_response.json()["id"])

    for invalid in (-1,):
        rejected = client.post(
            f"/app/invoices/{invoice_id}/lines",
            json={
                "line_type": "service",
                "description": "Invalid invoice price",
                "quantity_decimal": "1",
                "uom": "ea",
                "unit_price_cents": invalid,
            },
        )
        assert rejected.status_code in {400, 422}

    for literal in ("NaN", "Infinity", "-Infinity"):
        rejected = client.post(
            f"/app/invoices/{invoice_id}/lines",
            content=(
                '{"line_type":"service","description":"Invalid invoice price",'
                f'"quantity_decimal":"1","uom":"ea","unit_price_cents":{literal}}}'
            ),
            headers={"Content-Type": "application/json"},
        )
        assert rejected.status_code in {400, 422}

    zero_invoice_line = client.post(
        f"/app/invoices/{invoice_id}/lines",
        json={
            "line_type": "service",
            "description": "Valid free invoice line",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 0,
        },
    )
    assert zero_invoice_line.status_code == 200, zero_invoice_line.text
    rejected_invoice_update = client.patch(
        f"/app/invoices/{invoice_id}/lines/{zero_invoice_line.json()['id']}",
        json={"unit_price_cents": -10},
    )
    assert rejected_invoice_update.status_code == 400

    with bus_client["engine"].SessionLocal() as db:
        assert db.query(bus_client["jobs"].JobLine).filter(
            bus_client["jobs"].JobLine.job_id == job_id
        ).count() == 1
        assert db.query(bus_client["invoices"].InvoiceLine).filter(
            bus_client["invoices"].InvoiceLine.invoice_id == invoice_id
        ).count() == 1


def test_job_to_invoice_rejects_legacy_invalid_price_without_partial_invoice(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    job_response = client.post(
        "/app/jobs", json={"title": "Legacy invalid job", "contact_id": contact_id}
    )
    assert job_response.status_code == 200, job_response.text
    job_id = int(job_response.json()["id"])

    with bus_client["engine"].SessionLocal() as db:
        db.add(
            bus_client["jobs"].JobLine(
                job_id=job_id,
                line_type="service",
                description="Legacy negative price",
                qty_base=1000,
                display_uom="ea",
                unit_price_cents=-50,
                status="pending",
                sort_order=0,
            )
        )
        db.commit()

    cash_event_model = bus_client["models"].CashEvent
    rejected = client.post(f"/app/jobs/{job_id}/invoice", json={})
    assert rejected.status_code == 400
    assert "unit_price_cents_invalid" in rejected.text

    with bus_client["engine"].SessionLocal() as db:
        assert db.query(bus_client["invoices"].Invoice).filter(
            bus_client["invoices"].Invoice.job_id == job_id
        ).count() == 0
        assert db.query(cash_event_model).count() == 0
