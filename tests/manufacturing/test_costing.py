# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import json
import sys

import pytest
from fastapi.testclient import TestClient

from core.money import round_half_up_cents


@pytest.fixture()
def costing_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))

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
    client.headers.update({"X-Session-Token": session_token})

    with engine_module.SessionLocal() as db:
        output_item = models_module.Item(name="Output", uom="ea", qty_stored=0)
        input_item = models_module.Item(name="Input", uom="ea", qty_stored=3)
        db.add_all([output_item, input_item])
        db.flush()

        recipe = recipes_module.Recipe(name="Widget", output_item_id=output_item.id, output_qty=6.0)
        db.add(recipe)
        db.flush()

        db.add(
            recipes_module.RecipeItem(
                recipe_id=recipe.id,
                item_id=input_item.id,
                qty_required=3.0,
                is_optional=False,
            )
        )

        db.add_all(
            [
                models_module.ItemBatch(
                    item_id=input_item.id,
                    qty_initial=1.0,
                    qty_remaining=1.0,
                    unit_cost_cents=5,
                    source_kind="seed",
                    source_id=None,
                    is_oversold=False,
                ),
                models_module.ItemBatch(
                    item_id=input_item.id,
                    qty_initial=1.0,
                    qty_remaining=1.0,
                    unit_cost_cents=6,
                    source_kind="seed",
                    source_id=None,
                    is_oversold=False,
                ),
                models_module.ItemBatch(
                    item_id=input_item.id,
                    qty_initial=1.0,
                    qty_remaining=1.0,
                    unit_cost_cents=4,
                    source_kind="seed",
                    source_id=None,
                    is_oversold=False,
                ),
            ]
        )
        db.commit()

        recipe_id = recipe.id
        input_item_id = input_item.id
        output_item_id = output_item.id

    yield {
        "client": client,
        "engine": engine_module,
        "models": models_module,
        "recipes": recipes_module,
        "recipe_id": recipe_id,
        "input_item_id": input_item_id,
        "output_item_id": output_item_id,
    }


def test_unit_cost_round_half_up(costing_setup):
    client = costing_setup["client"]
    engine = costing_setup["engine"]
    models = costing_setup["models"]
    recipes = costing_setup["recipes"]

    assert round_half_up_cents(2.5) == 3
    assert round_half_up_cents(123456.5) == 123457
    assert round_half_up_cents(2.49) == 2

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": costing_setup["recipe_id"], "output_qty": 6},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["output_unit_cost_cents"] == 3

    with engine.SessionLocal() as db:
        run = db.get(recipes.ManufacturingRun, data["run_id"])
        assert run.status == "completed"
        meta = json.loads(run.meta)
        assert meta["cost_inputs_cents"] == 15
        assert meta["per_output_cents"] == 3

        output_batch = (
            db.query(models.ItemBatch)
            .filter(models.ItemBatch.source_kind == "manufacturing", models.ItemBatch.source_id == run.id)
            .one()
        )
        assert output_batch.unit_cost_cents == 3
        assert output_batch.qty_remaining == pytest.approx(6.0)
