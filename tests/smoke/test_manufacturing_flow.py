# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import json
import sys

import pytest
from fastapi.testclient import TestClient


MODULES_TO_RESET = [
    "core.api.http",
    "core.api.routes.manufacturing",
    "core.appdb.engine",
    "core.appdb.models",
    "core.appdb.models_recipes",
    "core.manufacturing.service",
    "core.services.models",
]


def bootstrap_app(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("BUS_DEV", "1")

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

    return {
        "client": client,
        "engine": engine_module,
        "models": models_module,
        "recipes": recipes_module,
    }


def snapshot_counts(db, models, recipes):
    return {
        "runs": db.query(recipes.ManufacturingRun).count(),
        "movements": db.query(models.ItemMovement).count(),
        "batches": db.query(models.ItemBatch).count(),
    }


def assert_counts_delta(before, after, *, runs=0, movements=0, batches=0):
    assert after["runs"] - before["runs"] == runs
    assert after["movements"] - before["movements"] == movements
    assert after["batches"] - before["batches"] == batches


@pytest.fixture()
def manufacturing_failfast_env(tmp_path, monkeypatch):
    env = bootstrap_app(tmp_path, monkeypatch)

    with env["engine"].SessionLocal() as db:
        output_item = env["models"].Item(name="Output", uom="ea", qty_stored=0)
        input_item = env["models"].Item(name="Input", uom="ea", qty_stored=0)
        db.add_all([output_item, input_item])
        db.flush()

        recipe = env["recipes"].Recipe(name="Widget", output_item_id=output_item.id, output_qty=1.0)
        db.add(recipe)
        db.flush()

        db.add(
            env["recipes"].RecipeItem(
                recipe_id=recipe.id,
                item_id=input_item.id,
                qty_required=5.0,
                is_optional=False,
            )
        )
        db.commit()

        recipe_id = recipe.id
        input_item_id = input_item.id

    yield {**env, "recipe_id": recipe_id, "input_item_id": input_item_id}


@pytest.fixture()
def manufacturing_success_env(tmp_path, monkeypatch):
    env = bootstrap_app(tmp_path, monkeypatch)

    with env["engine"].SessionLocal() as db:
        output_item = env["models"].Item(name="Output", uom="ea", qty_stored=0)
        input_item = env["models"].Item(name="Input", uom="ea", qty_stored=8)
        db.add_all([output_item, input_item])
        db.flush()

        recipe = env["recipes"].Recipe(name="Widget", output_item_id=output_item.id, output_qty=1.0)
        db.add(recipe)
        db.flush()

        db.add(
            env["recipes"].RecipeItem(
                recipe_id=recipe.id,
                item_id=input_item.id,
                qty_required=3.0,
                is_optional=False,
            )
        )

        db.add_all(
            [
                env["models"].ItemBatch(
                    item_id=input_item.id,
                    qty_initial=4.0,
                    qty_remaining=4.0,
                    unit_cost_cents=10,
                    source_kind="seed",
                    source_id=None,
                    is_oversold=False,
                ),
                env["models"].ItemBatch(
                    item_id=input_item.id,
                    qty_initial=4.0,
                    qty_remaining=4.0,
                    unit_cost_cents=20,
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
        **env,
        "recipe_id": recipe_id,
        "input_item_id": input_item_id,
        "output_item_id": output_item_id,
    }


def test_fail_fast_has_zero_new_movements_and_batches(manufacturing_failfast_env):
    client = manufacturing_failfast_env["client"]
    engine = manufacturing_failfast_env["engine"]
    models = manufacturing_failfast_env["models"]
    recipes = manufacturing_failfast_env["recipes"]

    with engine.SessionLocal() as db:
        before = snapshot_counts(db, models, recipes)

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": manufacturing_failfast_env["recipe_id"], "output_qty": 1},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"]["shortages"] == [
        {
            "item_id": manufacturing_failfast_env["input_item_id"],
            "required": 5.0,
            "available": 0.0,
        }
    ]

    with engine.SessionLocal() as db:
        after = snapshot_counts(db, models, recipes)

    assert_counts_delta(before, after, runs=0, movements=0, batches=0)


def test_success_has_expected_negative_moves_and_one_output_positive(manufacturing_success_env):
    client = manufacturing_success_env["client"]
    engine = manufacturing_success_env["engine"]
    models = manufacturing_success_env["models"]
    recipes = manufacturing_success_env["recipes"]

    with engine.SessionLocal() as db:
        before = snapshot_counts(db, models, recipes)

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": manufacturing_success_env["recipe_id"], "output_qty": 2},
    )

    assert resp.status_code == 200
    data = resp.json()

    with engine.SessionLocal() as db:
        after = snapshot_counts(db, models, recipes)
        assert_counts_delta(before, after, runs=1, movements=3, batches=1)

        run = db.get(recipes.ManufacturingRun, data["run_id"])
        assert run.status == "completed"
        meta = json.loads(run.meta)

        movements = (
            db.query(models.ItemMovement)
            .filter(models.ItemMovement.source_kind == "manufacturing", models.ItemMovement.source_id == run.id)
            .order_by(models.ItemMovement.id)
            .all()
        )
        negatives = [m for m in movements if m.qty_change < 0]
        positives = [m for m in movements if m.qty_change > 0]

        assert sorted([(m.batch_id, m.qty_change, m.unit_cost_cents) for m in negatives]) == [
            (1, -4.0, 10),
            (2, -2.0, 20),
        ]
        assert len(positives) == 1
        assert positives[0].qty_change == pytest.approx(2.0)
        assert positives[0].batch_id == meta["output_batch_id"]


def test_output_cost_equals_sum_inputs_over_qty(manufacturing_success_env):
    client = manufacturing_success_env["client"]
    engine = manufacturing_success_env["engine"]
    models = manufacturing_success_env["models"]
    recipes = manufacturing_success_env["recipes"]

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": manufacturing_success_env["recipe_id"], "output_qty": 2},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["output_unit_cost_cents"] == 40

    with engine.SessionLocal() as db:
        run = db.get(recipes.ManufacturingRun, data["run_id"])
        meta = json.loads(run.meta)
        assert meta["cost_inputs_cents"] == 80
        assert meta["per_output_cents"] == 40

        output_batch = (
            db.query(models.ItemBatch)
            .filter(models.ItemBatch.source_kind == "manufacturing", models.ItemBatch.source_id == run.id)
            .one()
        )
        assert output_batch.unit_cost_cents == 40
        assert output_batch.qty_remaining == pytest.approx(2.0)


def test_all_manufacturing_movements_is_oversold_zero(manufacturing_success_env):
    client = manufacturing_success_env["client"]
    engine = manufacturing_success_env["engine"]
    models = manufacturing_success_env["models"]

    resp = client.post(
        "/app/manufacturing/run",
        json={"recipe_id": manufacturing_success_env["recipe_id"], "output_qty": 2},
    )

    assert resp.status_code == 200

    with engine.SessionLocal() as db:
        manufacturing_movements = db.query(models.ItemMovement).filter(models.ItemMovement.source_kind == "manufacturing").all()

    assert all(not movement.is_oversold for movement in manufacturing_movements)
