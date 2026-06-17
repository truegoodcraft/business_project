from __future__ import annotations


def _create_contact(bus_client, name: str = "Job Invoice Contact") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        contact = models.Vendor(name=name, role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def _create_item(bus_client, name: str = "Invoice Widget") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        item = models.Item(name=name, dimension="count", uom="ea", qty_stored=0, is_product=True)
        db.add(item)
        db.commit()
        return int(item.id)


def _create_job(client, contact_id: int) -> dict:
    created = client.post("/app/jobs", json={"title": "Invoice Job", "contact_id": contact_id})
    assert created.status_code == 200, created.text
    return created.json()


def test_create_invoice_from_job_copies_billable_lines_only(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    item_id = _create_item(bus_client)
    job = _create_job(client, contact_id)

    product = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Widget run",
            "item_id": item_id,
            "quantity_decimal": "2",
            "uom": "ea",
            "unit_price_cents": 1200,
        },
    )
    assert product.status_code == 200, product.text
    fee = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "fee",
            "description": "Setup fee",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 500,
        },
    )
    assert fee.status_code == 200, fee.text
    note = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={"line_type": "note", "description": "Internal note"},
    )
    assert note.status_code == 200, note.text
    cancelled = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "service",
            "description": "Cancelled service",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 999,
            "status": "cancelled",
        },
    )
    assert cancelled.status_code == 200, cancelled.text

    invoice = client.post(f"/app/jobs/{job['id']}/invoice", json={"tax_rate_percent": "13"})
    assert invoice.status_code == 200, invoice.text
    payload = invoice.json()

    assert payload["invoice_number"] == "INV-1001"
    assert payload["status"] == "draft"
    assert payload["contact_id"] == contact_id
    assert payload["job_id"] == job["id"]
    assert [line["description"] for line in payload["lines"]] == ["Widget run", "Setup fee"]
    assert all(line["line_type"] in {"product", "fee"} for line in payload["lines"])
    assert payload["subtotal_cents"] == 2900
    assert payload["tax_cents"] == 377
    assert payload["total_cents"] == 3277


def test_later_job_edits_do_not_mutate_invoice_lines(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client, "Snapshot Contact")
    item_id = _create_item(bus_client, "Snapshot Widget")
    job = _create_job(client, contact_id)

    created_line = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Original description",
            "item_id": item_id,
            "quantity_decimal": "2",
            "uom": "ea",
            "unit_price_cents": 1000,
        },
    )
    assert created_line.status_code == 200, created_line.text
    job_line = created_line.json()

    created_invoice = client.post(f"/app/jobs/{job['id']}/invoice", json={})
    assert created_invoice.status_code == 200, created_invoice.text
    invoice = created_invoice.json()
    original_line = invoice["lines"][0]

    updated_job_line = client.patch(
        f"/app/jobs/{job['id']}/lines/{job_line['id']}",
        json={
            "description": "Changed later",
            "quantity_decimal": "5",
            "uom": "ea",
            "unit_price_cents": 2500,
        },
    )
    assert updated_job_line.status_code == 200, updated_job_line.text

    detail = client.get(f"/app/invoices/{invoice['id']}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["lines"][0]["description"] == original_line["description"] == "Original description"
    assert payload["lines"][0]["quantity_decimal"] == original_line["quantity_decimal"] == "2"
    assert payload["lines"][0]["unit_price_cents"] == original_line["unit_price_cents"] == 1000
