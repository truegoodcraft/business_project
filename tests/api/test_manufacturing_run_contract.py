# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.api, pytest.mark.bus_dev("1")]


@pytest.fixture()
def manufacturing_client(bus_client):
    env = bus_client
    return {
        "client": env["client"],
        "engine": env["engine"],
        "recipes": env["recipes"],
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
