# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient


MODULES_TO_RESET = [
    "core.api.http",
    "core.api.routes.manufacturing",
    "core.appdb.engine",
    "core.appdb.models",
    "core.appdb.models_recipes",
    "core.services.models",
]


@pytest.fixture()
def manufacturing_client_prod(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("BUS_DEV", "0")

    for module_name in MODULES_TO_RESET:
        sys.modules.pop(module_name, None)

    import core.appdb.engine as engine_module
    import core.appdb.models as models_module
    import core.appdb.models_recipes as recipes_module
    import core.services.models as services_models
    import core.api.http as api_http

    engine_module = importlib.reload(engine_module)
    models_module = importlib.reload(models_module)
    recipes_module = importlib.reload(recipes_module)
    services_models = importlib.reload(services_models)
    api_http = importlib.reload(api_http)

    from tgc.settings import Settings
    from tgc.state import init_state

    api_http.app.state.app_state = init_state(Settings())
    api_http.app.state.allow_writes = True

    models_module.Base.metadata.create_all(bind=engine_module.ENGINE)

    from core.config.writes import set_writes_enabled

    set_writes_enabled(True)

    client = TestClient(api_http.APP)
    session_token = api_http._load_or_create_token()
    api_http.app.state.app_state.tokens._rec.token = session_token
    client.headers.update({"Cookie": f"bus_session={session_token}"})

    yield client


def test_array_payload_sanitized(manufacturing_client_prod: TestClient):
    resp = manufacturing_client_prod.post("/app/manufacturing/run", json=[])

    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "bad_request"


def test_invalid_type_sanitized(manufacturing_client_prod: TestClient):
    resp = manufacturing_client_prod.post("/app/manufacturing/run", json="oops")

    assert resp.status_code == 400
    assert "error" in resp.json().get("detail", {})


def test_validation_error_envelope(manufacturing_client_prod: TestClient):
    resp = manufacturing_client_prod.post("/app/manufacturing/run")

    body = resp.json()
    assert resp.status_code == 400
    assert body["detail"]["error"] == "validation_error"
    assert body["detail"].get("fields")
