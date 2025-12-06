# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def manufacturing_client(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))

    for module_name in [
        "core.api.http",
        "core.api.routes.manufacturing",
        "core.appdb.engine",
        "core.appdb.models",
        "core.appdb.models_recipes",
        "core.services.models",
    ]:
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
    client.headers.update({"X-Session-Token": session_token})

    yield {
        "client": client,
        "engine": engine_module,
        "recipes": recipes_module,
    }


def _run_count(engine_module, recipes_module) -> int:
    with engine_module.SessionLocal() as db:
        return db.query(recipes_module.ManufacturingRun).count()


def test_rejects_array_payload(manufacturing_client):
    client = manufacturing_client["client"]
    engine = manufacturing_client["engine"]
    recipes = manufacturing_client["recipes"]

    resp = client.post("/app/manufacturing/run", json=[])

    assert resp.status_code == 400
    assert resp.json() == {"detail": "single run only"}
    assert _run_count(engine, recipes) == 0


def test_adhoc_components_required(manufacturing_client):
    client = manufacturing_client["client"]
    engine = manufacturing_client["engine"]
    recipes = manufacturing_client["recipes"]

    resp = client.post(
        "/app/manufacturing/run",
        json={"output_item_id": 1, "output_qty": 2},
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "components required for ad-hoc run"}
    assert _run_count(engine, recipes) == 0


def test_recipe_and_adhoc_mutually_exclusive(manufacturing_client):
    client = manufacturing_client["client"]
    engine = manufacturing_client["engine"]
    recipes = manufacturing_client["recipes"]

    resp = client.post(
        "/app/manufacturing/run",
        json={
            "recipe_id": 1,
            "output_item_id": 2,
            "output_qty": 1,
            "components": [{"item_id": 1, "qty_required": 1}],
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "recipe and ad-hoc payloads are mutually exclusive"}
    assert _run_count(engine, recipes) == 0
