from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ui_dimension_for_unit(unit: str) -> str:
    script = (
        "import('./core/ui/js/lib/units.js')"
        f".then(m => console.log(JSON.stringify(m.dimensionForUnit({unit!r}))));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return str(json.loads(result.stdout))


@pytest.mark.parametrize(
    ("unit", "dimension"),
    [
        ("mg", "weight"),
        ("g", "weight"),
        ("kg", "weight"),
        ("mm", "length"),
        ("cm", "length"),
        ("m", "length"),
        ("ml", "volume"),
        ("l", "volume"),
        ("mm3", "volume"),
        ("cm3", "volume"),
        ("m3", "volume"),
        ("mm2", "area"),
        ("cm2", "area"),
        ("m2", "area"),
        ("ea", "count"),
        ("mc", "count"),
    ],
)
def test_ui_unit_helper_maps_units_to_backend_dimensions(unit: str, dimension: str):
    assert _ui_dimension_for_unit(unit) == dimension


@pytest.mark.parametrize("uom", ["mg", "g", "kg"])
def test_create_item_accepts_weight_uoms(bus_client: dict[str, Any], uom: str):
    response = bus_client["client"].post(
        "/app/items",
        json={"name": f"Weight item {uom}", "dimension": "weight", "uom": uom, "price": 1.0},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dimension"] == "weight"
    assert body["uom"] == uom


def test_filament_stock_in_grams_stores_mg_base_units(bus_client: dict[str, Any]):
    client = bus_client["client"]
    engine = bus_client["engine"]
    models = bus_client["models"]

    item_response = client.post(
        "/app/items",
        json={"name": "SUNLU PLA 2.0 Red", "dimension": "weight", "uom": "g", "price": 0},
    )
    assert item_response.status_code == 200, item_response.text
    item_id = int(item_response.json()["id"])

    stock_response = client.post(
        "/app/stock/in",
        json={"item_id": item_id, "quantity_decimal": "1000", "uom": "g", "unit_cost_cents": 2},
    )
    assert stock_response.status_code == 200, stock_response.text

    with engine.SessionLocal() as db:
        item = db.get(models.Item, item_id)
        assert item is not None
        assert item.dimension == "weight"
        assert item.uom == "g"
        assert int(item.qty_stored) == 1_000_000
        batch = db.query(models.ItemBatch).filter(models.ItemBatch.item_id == item_id).one()
        assert int(batch.qty_initial) == 1_000_000
        assert int(batch.qty_remaining) == 1_000_000


def test_create_item_rejects_invalid_dimension(bus_client: dict[str, Any]):
    response = bus_client["client"].post(
        "/app/items",
        json={"name": "Bad dimension", "dimension": "temperature", "uom": "g"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported dimension"


def test_add_item_ui_payload_shape_for_grams_with_opening_batch(bus_client: dict[str, Any]):
    client = bus_client["client"]
    engine = bus_client["engine"]
    models = bus_client["models"]
    unit = "g"
    dimension = _ui_dimension_for_unit(unit)

    item_response = client.post(
        "/app/items",
        json={
            "name": "UI PLA payload",
            "dimension": dimension,
            "uom": unit,
            "unit": unit,
            "display_unit": unit,
            "is_product": False,
        },
    )
    assert item_response.status_code == 200, item_response.text
    item_id = int(item_response.json()["id"])

    stock_response = client.post(
        "/app/stock/in",
        json={"item_id": item_id, "quantity_decimal": "420", "uom": unit, "unit_cost_cents": 0},
    )
    assert stock_response.status_code == 200, stock_response.text

    with engine.SessionLocal() as db:
        item = db.get(models.Item, item_id)
        assert item is not None
        assert item.dimension == "weight"
        assert item.uom == "g"
        assert int(item.qty_stored) == 420_000
        batch = db.query(models.ItemBatch).filter(models.ItemBatch.item_id == item_id).one()
        assert int(batch.qty_remaining) == 420_000