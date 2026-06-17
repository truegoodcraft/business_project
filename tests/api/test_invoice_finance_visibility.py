from __future__ import annotations


def _create_contact(bus_client, name: str = "Finance Invoice Contact") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        contact = models.Vendor(name=name, role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def test_invoice_payment_appears_in_finance_summary_and_transactions(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    invoice = client.post("/app/invoices", json={"contact_id": contact_id, "tax_rate_percent": "10"}).json()
    client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "service",
            "description": "Revenue line",
            "quantity_decimal": "2",
            "uom": "ea",
            "unit_price_cents": 1000,
            "taxable": True,
        },
    )
    client.post(f"/app/invoices/{invoice['id']}/issue", json={})
    client.post(f"/app/invoices/{invoice['id']}/mark-paid", json={"paid_at": "2026-06-17T12:00:00"})

    summary = client.get("/app/finance/summary?from=2026-06-17&to=2026-06-17")
    assert summary.status_code == 200, summary.text
    assert summary.json()["gross_sales_cents"] == 2200
    assert summary.json()["net_sales_cents"] == 2200

    transactions = client.get("/app/finance/transactions?from=2026-06-17&to=2026-06-17&limit=20")
    assert transactions.status_code == 200, transactions.text
    rows = [
        row
        for row in transactions.json()["transactions"]
        if row["kind"] == "sale" and row["source_id"] == f"invoice:{invoice['id']}"
    ]
    assert len(rows) == 1
    assert rows[0]["amount_cents"] == 2200
