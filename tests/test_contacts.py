# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def contacts_client(tmp_path, monkeypatch):
    # Isolate DB for each test run
    home = tmp_path / "buscore"
    monkeypatch.setenv("BUSCORE_HOME", str(home))
    home.mkdir(parents=True, exist_ok=True)
    (home / "app").mkdir(parents=True, exist_ok=True)

    for module_name in [
        "tgc.http",
        "core.appdb.models",
        "core.appdb.engine",
        "core.services.models",
        "core.api.routes.vendors",
        "core.api.routes.items",
        "core.appdb.session",
    ]:
        sys.modules.pop(module_name, None)

    import core.appdb.engine as engine_module
    import core.appdb.models as models_module
    import core.services.models as services_models
    import tgc.http as api_http

    # Reload modules so they pick up the isolated BUSCORE_HOME
    engine_module = importlib.reload(engine_module)
    models_module = importlib.reload(models_module)
    services_models = importlib.reload(services_models)
    api_http = importlib.reload(api_http)

    models_module.Base.metadata.create_all(bind=engine_module.ENGINE)

    # Initialize application state and schema without relying on lifespan hooks.
    api_http.app.state.app_state = api_http.init_state(api_http.Settings())
    api_http._run_startup_migrations()
    from core.config.writes import set_writes_enabled

    set_writes_enabled(True)

    with engine_module.SessionLocal() as db:
        db.query(models_module.Vendor).delete()
        db.commit()
        assert db.query(models_module.Vendor).count() == 0

    client = TestClient(api_http.app)
    token_resp = client.get("/session/token/plain")
    token = token_resp.text
    client.headers.update({"X-Session-Token": token})

    with engine_module.SessionLocal() as db:
        db.query(models_module.Vendor).delete()
        db.commit()

    return {
        "client": client,
        "engine": engine_module,
        "models": models_module,
    }


def test_get_contacts_returns_empty_list(contacts_client):
    client = contacts_client["client"]

    resp = client.get("/app/contacts")

    assert resp.status_code == 200
    assert resp.json() == []


def test_create_contact_defaults_to_flags_false(contacts_client):
    client = contacts_client["client"]

    resp = client.post("/app/contacts", json={"name": "Alice"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["is_vendor"] is False
    assert data["is_org"] is False

    vendor_resp = client.post("/app/contacts", json={"name": "Bob", "is_vendor": True})
    assert vendor_resp.status_code == 201


def test_contact_filters_by_vendor_and_org_flags(contacts_client):
    client = contacts_client["client"]
    engine = contacts_client["engine"]
    models = contacts_client["models"]

    with engine.SessionLocal() as db:
        db.query(models.Vendor).delete()
        db.add_all(
            [
                models.Vendor(name="Bob", is_vendor=1, role="vendor"),
                models.Vendor(name="Carol", is_vendor=0, role="contact"),
                models.Vendor(name="OrgCo", is_vendor=0, is_org=1, role="contact"),
            ]
        )
        db.commit()
        names = {v.name for v in db.query(models.Vendor).all()}
        assert names == {"Bob", "Carol", "OrgCo"}

    vendors = client.get("/app/contacts", params={"is_vendor": "true"})
    assert vendors.status_code == 200
    assert {v["name"] for v in vendors.json()} == {"Bob"}

    non_vendors = client.get("/app/contacts", params={"is_vendor": "false"})
    assert non_vendors.status_code == 200
    assert {v["name"] for v in non_vendors.json()} == {"Carol", "OrgCo"}

    orgs = client.get("/app/contacts", params={"is_org": "true"})
    assert orgs.status_code == 200
    assert {v["name"] for v in orgs.json()} == {"OrgCo"}

    # Verify vendor endpoint with same filters still works
    vendor_orgs = client.get("/app/vendors", params={"is_org": "true"})
    assert vendor_orgs.status_code == 200
    assert {v["name"] for v in vendor_orgs.json()} == {"OrgCo"}
