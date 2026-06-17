from __future__ import annotations


def _create_contact(bus_client, name: str = "Invoice Contact") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        contact = models.Vendor(name=name, role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def _create_invoice(client, contact_id: int, **payload) -> dict:
    response = client.post("/app/invoices", json={"contact_id": contact_id, **payload})
    assert response.status_code == 200, response.text
    return response.json()


def test_invoice_number_starts_at_inv_1001(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)

    first = _create_invoice(client, contact_id)
    second = _create_invoice(client, contact_id)

    assert first["invoice_number"] == "INV-1001"
    assert second["invoice_number"] == "INV-1002"


def test_manual_invoice_create_and_draft_line_crud(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    invoice = _create_invoice(client, contact_id, tax_rate_percent="13")

    assert invoice["status"] == "draft"
    assert invoice["subtotal_cents"] == 0
    assert invoice["tax_rate_percent"] == "13"

    created = client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "service",
            "description": "Design work",
            "quantity_decimal": "2.5",
            "uom": "hr",
            "unit_price_cents": 1000,
            "taxable": True,
        },
    )
    assert created.status_code == 200, created.text
    created_line = created.json()
    assert created_line["line_subtotal_cents"] == 2500

    updated = client.patch(
        f"/app/invoices/{invoice['id']}/lines/{created_line['id']}",
        json={
            "quantity_decimal": "3",
            "uom": "hr",
            "taxable": False,
        },
    )
    assert updated.status_code == 200, updated.text
    updated_line = updated.json()
    assert updated_line["line_subtotal_cents"] == 3000
    assert updated_line["taxable"] is False

    detail = client.get(f"/app/invoices/{invoice['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["subtotal_cents"] == 3000
    assert detail.json()["tax_cents"] == 0
    assert detail.json()["total_cents"] == 3000

    deleted = client.delete(f"/app/invoices/{invoice['id']}/lines/{created_line['id']}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json() == {"ok": True, "deleted": created_line["id"]}

    detail_after_delete = client.get(f"/app/invoices/{invoice['id']}")
    assert detail_after_delete.json()["lines"] == []
    assert detail_after_delete.json()["total_cents"] == 0


def test_invoice_totals_taxable_toggle_and_issue_rules(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    invoice = _create_invoice(client, contact_id, tax_rate_percent="13")

    taxable = client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "service",
            "description": "Taxable labor",
            "quantity_decimal": "2",
            "uom": "hr",
            "unit_price_cents": 1000,
            "taxable": True,
        },
    )
    assert taxable.status_code == 200, taxable.text
    non_taxable = client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "fee",
            "description": "Non-taxable fee",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 500,
            "taxable": False,
        },
    )
    assert non_taxable.status_code == 200, non_taxable.text

    detail = client.get(f"/app/invoices/{invoice['id']}")
    payload = detail.json()
    assert payload["subtotal_cents"] == 2500
    assert payload["tax_cents"] == 260
    assert payload["total_cents"] == 2760

    empty_invoice = _create_invoice(client, contact_id)
    issue_empty = client.post(f"/app/invoices/{empty_invoice['id']}/issue", json={})
    assert issue_empty.status_code == 400
    assert issue_empty.json()["detail"] == "invoice_issue_requires_line"

    issued = client.post(f"/app/invoices/{invoice['id']}/issue", json={})
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "issued"
    assert issued.json()["issue_date"] is not None


def test_paid_invoice_cannot_be_financially_edited_and_void_invoice_cannot_be_paid(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)
    invoice = _create_invoice(client, contact_id, tax_rate_percent="10")
    created = client.post(
        f"/app/invoices/{invoice['id']}/lines",
        json={
            "line_type": "service",
            "description": "Consulting",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 2000,
        },
    )
    assert created.status_code == 200, created.text
    line = created.json()

    issued = client.post(f"/app/invoices/{invoice['id']}/issue", json={})
    assert issued.status_code == 200, issued.text
    paid = client.post(f"/app/invoices/{invoice['id']}/mark-paid", json={})
    assert paid.status_code == 200, paid.text

    edit_line = client.patch(
        f"/app/invoices/{invoice['id']}/lines/{line['id']}",
        json={"unit_price_cents": 2500},
    )
    assert edit_line.status_code == 400
    assert edit_line.json()["detail"] == "invoice_edit_forbidden_after_paid"

    edit_header = client.patch(f"/app/invoices/{invoice['id']}", json={"tax_rate_percent": "15"})
    assert edit_header.status_code == 400
    assert edit_header.json()["detail"] == "invoice_edit_forbidden_after_paid"

    voidable = _create_invoice(client, contact_id)
    created_voidable = client.post(
        f"/app/invoices/{voidable['id']}/lines",
        json={
            "line_type": "service",
            "description": "Void me",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 500,
        },
    )
    assert created_voidable.status_code == 200, created_voidable.text
    voided = client.post(f"/app/invoices/{voidable['id']}/void", json={})
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "void"

    pay_void = client.post(f"/app/invoices/{voidable['id']}/mark-paid", json={})
    assert pay_void.status_code == 400
    assert pay_void.json()["detail"] == "invoice_void_cannot_be_paid"
