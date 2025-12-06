# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def manufacturing_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("BUS_DEV", "1")

    for module_name in [
        "core.api.http",
        "core.api.routes.manufacturing",
        "core.appdb.engine",
        "core.appdb.models",
        "core.appdb.models_recipes",
        "core.manufacturing.service",
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
    client.headers.update({"Cookie": f"bus_session={session_token}"})

    with engine_module.SessionLocal() as db:
        output_item = models_module.Item(name="Output", uom="ea", qty_stored=0)
        input_item = models_module.Item(name="Input", uom="ea", qty_stored=0)
        db.add_all([output_item, input_item])
        db.flush()

        recipe = recipes_module.Recipe(name="Widget", output_item_id=output_item.id, output_qty=1.0)
        db.add(recipe)
        db.flush()

        db.add(
            recipes_module.RecipeItem(
                recipe_id=recipe.id,
                item_id=input_item.id,
                qty_required=5.0,
                is_optional=False,
            )
        )
        db.commit()

        recipe_id = recipe.id
        input_item_id = input_item.id

    yield {
        "client": client,
        "engine": engine_module,
        "models": models_module,
        "recipes": recipes_module,
        "recipe_id": recipe_id,
        "input_item_id": input_item_id,
    }


def test_shortage_returns_400_and_no_movements(manufacturing_setup):
    client = manufacturing_setup["client"]
    engine = manufacturing_setup["engine"]
    models = manufacturing_setup["models"]
    recipes = manufacturing_setup["recipes"]

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": manufacturing_setup["recipe_id"], "output_qty": 1},
    )

    assert resp.status_code == 400
    assert resp.json() == {
        "detail": {
            "shortages": [
                {
                    "item_id": manufacturing_setup["input_item_id"],
                    "required": 5.0,
                    "available": 0.0,
                }
            ]
        }
    }

    with engine.SessionLocal() as db:
        assert db.query(recipes.ManufacturingRun).count() == 0
        assert db.query(models.ItemMovement).count() == 0
        assert db.query(models.ItemBatch).count() == 0
