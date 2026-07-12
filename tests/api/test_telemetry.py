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


def test_module_event_endpoint_accepts_only_coarse_allowlist(bus_client, monkeypatch):
    from core.api.routes import telemetry as telemetry_routes

    emitted: list[tuple[str, bool | None]] = []
    monkeypatch.setattr(
        telemetry_routes,
        "emit_telemetry",
        lambda name, deduplicate=None: emitted.append((name, deduplicate)) or True,
    )
    accepted = bus_client["client"].post(
        "/app/telemetry/event",
        json={"event_name": "inventory_opened"},
    )
    assert accepted.status_code == 200
    assert accepted.json() == {"ok": True, "queued": True}
    assert emitted == [("inventory_opened", False)]

    prohibited = bus_client["client"].post(
        "/app/telemetry/event",
        json={"event_name": "customer_opened"},
    )
    assert prohibited.status_code == 200
    assert prohibited.json() == {"ok": True, "queued": False}

    extra = bus_client["client"].post(
        "/app/telemetry/event",
        json={"event_name": "inventory_opened", "item_name": "private"},
    )
    assert extra.status_code == 400
