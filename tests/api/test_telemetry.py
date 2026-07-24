from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.api


def test_preference_opt_out_is_available_and_clears_queue(bus_client, monkeypatch):
    from core.api.routes import telemetry as telemetry_routes

    cleared: list[bool] = []
    monkeypatch.setattr(telemetry_routes, "clear_telemetry_queue", lambda: cleared.append(True))
    response = bus_client["client"].post("/app/telemetry/preference", json={"enabled": False})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "enabled": False}
    assert cleared == [True]

    config_path = bus_client["local_app_data"] / "BUSCore" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["telemetry"] == {"enabled": False, "disclosure_acknowledged": True}


def test_repeated_module_event_endpoint_is_not_exposed(bus_client):
    response = bus_client["client"].post(
        "/app/telemetry/event",
        json={"event_name": "inventory_opened"},
    )
    assert response.status_code == 404


def test_telemetry_status_exposes_delivery_health(bus_client, monkeypatch):
    from core.api.routes import telemetry as telemetry_routes

    monkeypatch.setattr(
        telemetry_routes,
        "telemetry_status",
        lambda: {
            "enabled": True,
            "pending_count": 2,
            "acknowledged_count": 8,
            "rejected_count": 1,
            "dead_letter_count": 1,
            "last_successful_delivery_at": "2026-07-24T12:00:00.000Z",
            "last_status": 202,
            "last_error_category": None,
        },
    )
    response = bus_client["client"].get("/app/telemetry/status")
    assert response.status_code == 200
    assert response.json()["pending_count"] == 2
    assert response.json()["acknowledged_count"] == 8


def test_successful_stock_and_invoice_outcomes_emit_milestones(bus_client, monkeypatch):
    emitted: list[str] = []
    monkeypatch.setattr(
        bus_client["api_http"],
        "emit_telemetry",
        lambda name, deduplicate=None: emitted.append(name) or True,
    )
    client = bus_client["client"]

    item = client.post("/app/items", json={"name": "Outcome material", "dimension": "count", "uom": "ea"})
    assert item.status_code == 200, item.text
    stock = client.post(
        "/app/stock/in",
        json={"item_id": item.json()["id"], "quantity_decimal": "2", "uom": "ea", "unit_cost_cents": 100},
    )
    assert stock.status_code == 200, stock.text

    contact = client.post("/app/contacts", json={"name": "Outcome customer"})
    assert contact.status_code == 201, contact.text
    invoice = client.post("/app/invoices", json={"contact_id": contact.json()["id"]})
    assert invoice.status_code == 200, invoice.text
    line = client.post(
        f"/app/invoices/{invoice.json()['id']}/lines",
        json={
            "line_type": "service",
            "description": "Outcome item",
            "quantity_decimal": "1",
            "uom": "hr",
            "unit_price_cents": 200,
            "taxable": True,
        },
    )
    assert line.status_code == 200, line.text
    issued = client.post(f"/app/invoices/{invoice.json()['id']}/issue", json={})
    assert issued.status_code == 200, issued.text
    paid = client.post(f"/app/invoices/{invoice.json()['id']}/mark-paid", json={})
    assert paid.status_code == 200, paid.text

    assert "first_stock_recorded" in emitted
    assert "first_contact_created" in emitted
    assert "first_invoice_issued" in emitted
    assert "first_invoice_paid" not in emitted
