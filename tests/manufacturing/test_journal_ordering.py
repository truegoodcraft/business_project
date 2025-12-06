# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def manufacturing_journal_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    journal_path = tmp_path / "journals" / "manufacturing.jsonl"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("BUS_MANUFACTURING_JOURNAL", str(journal_path))

    for module_name in [
        "core.api.http",
        "core.api.routes.manufacturing",
        "core.appdb.engine",
        "core.appdb.models",
        "core.appdb.models_recipes",
        "core.journal.manufacturing",
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
        input_item = models_module.Item(name="Input", uom="ea", qty_stored=2)
        db.add_all([output_item, input_item])
        db.flush()

        recipe = recipes_module.Recipe(name="Widget", output_item_id=output_item.id, output_qty=1.0)
        db.add(recipe)
        db.flush()

        db.add(
            recipes_module.RecipeItem(
                recipe_id=recipe.id,
                item_id=input_item.id,
                qty_required=1.0,
                is_optional=False,
            )
        )

        db.add(
            models_module.ItemBatch(
                item_id=input_item.id,
                qty_initial=2.0,
                qty_remaining=2.0,
                unit_cost_cents=10,
                source_kind="seed",
                source_id=None,
                is_oversold=False,
            )
        )

        db.commit()

        recipe_id = recipe.id

    yield {
        "client": client,
        "engine": engine_module,
        "models": models_module,
        "recipes": recipes_module,
        "recipe_id": recipe_id,
        "journal_path": journal_path,
    }


def test_append_failure_does_not_rollback(manufacturing_journal_setup, monkeypatch):
    client = manufacturing_journal_setup["client"]
    engine = manufacturing_journal_setup["engine"]
    models = manufacturing_journal_setup["models"]
    recipes = manufacturing_journal_setup["recipes"]
    recipe_id = manufacturing_journal_setup["recipe_id"]

    def boom(_entry):
        raise RuntimeError("fsync failed")

    monkeypatch.setattr("core.api.routes.manufacturing.append_mfg_journal", boom)

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": recipe_id, "output_qty": 1},
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    with engine.SessionLocal() as db:
        run = db.query(recipes.ManufacturingRun).one()
        assert run.status == "completed"

        movements = db.query(models.ItemMovement).filter(
            models.ItemMovement.source_kind == "manufacturing",
            models.ItemMovement.source_id == run.id,
        )

        assert movements.count() == 2
        qty_total = sum(m.qty_change for m in movements)
        assert abs(qty_total - 0) < 1e-9
