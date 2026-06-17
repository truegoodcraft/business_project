from __future__ import annotations


def _create_contact(bus_client, name: str = "Mark Paid Contact") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        contact = models.Vendor(name=name, role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def _create_issued_invoice(client, contact_id: int) -> dict:
    created = client.post("/app/invoices", json={"contact_id": contact_id, "tax_rate_percent": "10"})
    assert created.status_code == 200, created.text
    invoice = created.json()
    line = client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "service",
            "description": "Bench work",
            "quantity_decimal": "2",
            "uom": "ea",
            "unit_price_cents": 1500,
            "taxable": True,
        },
    )
    assert line.status_code == 200, line.text
    issued = client.post(f"/app/invoices/{invoice['id']}/issue", json={})
    assert issued.status_code == 200, issued.text
    return issued.json()


def test_mark_paid_creates_exactly_one_cash_event_and_no_stock_side_effects(bus_client):
    client = bus_client["client"]
    models = bus_client["models"]
    engine = bus_client["engine"]
    contact_id = _create_contact(bus_client)
    invoice = _create_issued_invoice(client, contact_id)

    with engine.SessionLocal() as db:
        before_events = db.query(models.CashEvent).count()
        before_movements = db.query(models.ItemMovement).count()
        before_batches = db.query(models.ItemBatch).count()

    response = client.post(f"/app/invoices/{invoice['id']}/mark-paid", json={})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "paid"
    assert payload["paid_cash_event_id"] is not None

    with engine.SessionLocal() as db:
        cash_event = db.get(models.CashEvent, int(payload["paid_cash_event_id"]))
        assert cash_event is not None
        assert cash_event.kind == "sale"
        assert cash_event.category == "invoice"
        assert cash_event.source_kind == "invoice"
        assert cash_event.source_id == f"invoice:{invoice['id']}"
        assert int(cash_event.amount_cents) == int(payload["total_cents"])
        assert cash_event.item_id is None
        assert cash_event.qty_base is None
        assert cash_event.unit_price_cents is None
        after_events = db.query(models.CashEvent).count()
        after_movements = db.query(models.ItemMovement).count()
        after_batches = db.query(models.ItemBatch).count()

    assert after_events == before_events + 1
    assert after_movements == before_movements
    assert after_batches == before_batches


def test_mark_paid_twice_is_idempotent(bus_client):
    client = bus_client["client"]
    models = bus_client["models"]
    engine = bus_client["engine"]
    contact_id = _create_contact(bus_client, "Idempotent Contact")
    invoice = _create_issued_invoice(client, contact_id)

    first = client.post(f"/app/invoices/{invoice['id']}/mark-paid", json={})
    assert first.status_code == 200, first.text
    first_payload = first.json()

    with engine.SessionLocal() as db:
        before_count = db.query(models.CashEvent).count()

    second = client.post(f"/app/invoices/{invoice['id']}/mark-paid", json={})
    assert second.status_code == 200, second.text
    second_payload = second.json()

    with engine.SessionLocal() as db:
        after_count = db.query(models.CashEvent).count()

    assert second_payload["status"] == "paid"
    assert second_payload["paid_cash_event_id"] == first_payload["paid_cash_event_id"]
    assert after_count == before_count
