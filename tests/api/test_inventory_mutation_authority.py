# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.api


def _journal_bytes() -> bytes:
    path = Path(os.environ["BUS_INVENTORY_JOURNAL"])
    return path.read_bytes() if path.exists() else b""


def _inventory_counts(env: dict, item_id: int) -> tuple[int, int, int, int]:
    models = env["models"]
    with env["engine"].SessionLocal() as db:
        item = db.get(models.Item, item_id)
        assert item is not None
        return (
            int(item.qty_stored or 0),
            db.query(models.ItemBatch).filter(models.ItemBatch.item_id == item_id).count(),
            db.query(models.ItemMovement).filter(models.ItemMovement.item_id == item_id).count(),
            db.query(models.CashEvent).filter(models.CashEvent.item_id == item_id).count(),
        )


def test_item_metadata_cannot_mutate_inventory_authority(bus_client):
    client = bus_client["client"]

    rejected_create = client.post(
        "/app/items",
        json={"name": "Injected stock", "dimension": "count", "uom": "ea", "qty_stored": 5000},
    )
    assert rejected_create.status_code == 400
    assert "inventory_quantity_requires_stock_movement" in rejected_create.text

    created = client.post(
        "/app/items",
        json={"name": "Authority item", "dimension": "count", "uom": "ea", "price": 2},
    )
    assert created.status_code == 200, created.text
    item_id = int(created.json()["id"])
    assert _inventory_counts(bus_client, item_id) == (0, 0, 0, 0)

    stock_in = client.post(
        "/app/stock/in",
        json={"item_id": item_id, "quantity_decimal": "3", "uom": "ea", "unit_cost_cents": 25},
    )
    assert stock_in.status_code == 200, stock_in.text
    before = _inventory_counts(bus_client, item_id)
    before_journal = _journal_bytes()

    for quantity_payload in ({"qty": 99}, {"qty_stored": 99000}):
        response = client.put(
            f"/app/items/{item_id}",
            json={"name": "Metadata only", **quantity_payload},
        )
        assert response.status_code == 400
        assert "inventory_quantity_requires_stock_movement" in response.text
        assert _inventory_counts(bus_client, item_id) == before
        assert _journal_bytes() == before_journal

    stock_out = client.post(
        "/app/stock/out",
        json={"item_id": item_id, "quantity_decimal": "1", "uom": "ea", "reason": "sold"},
    )
    assert stock_out.status_code == 200, stock_out.text
    after = _inventory_counts(bus_client, item_id)
    assert after[0] == before[0] - 1000
    assert after[1] == before[1]
    assert after[2] == before[2] + 1
    assert after[3] == before[3] + 1
    assert _journal_bytes() != before_journal


def test_invalid_item_prices_fail_before_metadata_mutation(bus_client):
    client = bus_client["client"]
    invalid_values = (-1, "not-a-price")

    for index, value in enumerate(invalid_values):
        response = client.post(
            "/app/items",
            json={"name": f"Bad price {index}", "dimension": "count", "uom": "ea", "price": value},
        )
        assert response.status_code == 400
        assert "item_price_invalid" in response.text

    for literal in ("NaN", "Infinity", "-Infinity"):
        response = client.post(
            "/app/items",
            content=(
                '{"name":"Non-finite price","dimension":"count",'
                f'"uom":"ea","price":{literal}}}'
            ),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert "item_price_invalid" in response.text

    created = client.post(
        "/app/items",
        json={"name": "Stable price", "dimension": "count", "uom": "ea", "price": 0},
    )
    assert created.status_code == 200, created.text
    item_id = int(created.json()["id"])

    for value in invalid_values:
        response = client.put(
            f"/app/items/{item_id}",
            json={"name": "Must not apply", "price": value},
        )
        assert response.status_code == 400
        with bus_client["engine"].SessionLocal() as db:
            item = db.get(bus_client["models"].Item, item_id)
            assert item is not None
            assert item.name == "Stable price"
            assert float(item.price) == 0

    for literal in ("NaN", "Infinity", "-Infinity"):
        response = client.put(
            f"/app/items/{item_id}",
            content=f'{{"name":"Must not apply","price":{literal}}}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        with bus_client["engine"].SessionLocal() as db:
            item = db.get(bus_client["models"].Item, item_id)
            assert item is not None
            assert item.name == "Stable price"
            assert float(item.price) == 0


def test_invalid_legacy_stored_price_cannot_partially_sell_stock(bus_client):
    client = bus_client["client"]
    models = bus_client["models"]

    created = client.post(
        "/app/items",
        json={"name": "Legacy bad price", "dimension": "count", "uom": "ea", "price": 1},
    )
    assert created.status_code == 200, created.text
    item_id = int(created.json()["id"])
    stocked = client.post(
        "/app/stock/in",
        json={"item_id": item_id, "quantity_decimal": "2", "uom": "ea", "unit_cost_cents": 10},
    )
    assert stocked.status_code == 200, stocked.text

    with bus_client["engine"].SessionLocal() as db:
        item = db.get(models.Item, item_id)
        assert item is not None
        item.price = -5
        db.commit()

    before = _inventory_counts(bus_client, item_id)
    before_journal = _journal_bytes()
    rejected = client.post(
        "/app/stock/out",
        json={"item_id": item_id, "quantity_decimal": "1", "uom": "ea", "reason": "sold"},
    )
    assert rejected.status_code == 400
    assert "stored_item_price_invalid" in rejected.text
    assert _inventory_counts(bus_client, item_id) == before
    assert _journal_bytes() == before_journal
