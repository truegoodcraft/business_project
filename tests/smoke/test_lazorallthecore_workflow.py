# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _item_id(payload: dict) -> int:
    item = payload.get("item") if isinstance(payload, dict) and "item" in payload else payload
    assert isinstance(item, dict)
    return int(item["id"])


def test_lazorallthecore_first_workflow_smoke(bus_client):
    client = bus_client["client"]

    vendor = client.post(
        "/app/contacts",
        json={"name": "Workflow Vendor", "contact": "workflow@example.test", "is_vendor": True},
    )
    assert vendor.status_code == 201, vendor.text
    vendor_id = int(vendor.json()["id"])

    material = client.post(
        "/app/items",
        json={
            "name": "Leatherette Patch",
            "dimension": "count",
            "uom": "ea",
            "type": "Material",
            "vendor_id": vendor_id,
        },
    )
    assert material.status_code == 200, material.text
    material_payload = material.json()
    material_id = _item_id(material_payload)
    assert material_payload["vendor_id"] == vendor_id

    product = client.post(
        "/app/items",
        json={
            "name": "Skull Patch",
            "dimension": "count",
            "uom": "ea",
            "type": "Product",
            "is_product": True,
            "price": 10.00,
        },
    )
    assert product.status_code == 200, product.text
    product_id = _item_id(product.json())

    stock_in = client.post(
        "/app/purchase",
        json={
            "item_id": material_id,
            "quantity_decimal": "5",
            "uom": "ea",
            "unit_cost_cents": 100,
            "source_id": "workflow-material-stock",
        },
    )
    assert stock_in.status_code == 200, stock_in.text

    recipe = client.post(
        "/app/recipes",
        json={
            "name": "Skull Patch Recipe",
            "output_item_id": product_id,
            "quantity_decimal": "1",
            "uom": "ea",
            "items": [
                {
                    "item_id": material_id,
                    "quantity_decimal": "2",
                    "uom": "ea",
                    "optional": False,
                    "sort": 0,
                }
            ],
        },
    )
    assert recipe.status_code == 200, recipe.text
    recipe_id = int(recipe.json()["id"])

    shortage = client.post(
        "/app/manufacture",
        json={"recipe_id": recipe_id, "quantity_decimal": "3", "uom": "ea"},
    )
    assert shortage.status_code == 400, shortage.text
    detail = shortage.json()["detail"]
    assert detail["error"] == "insufficient_stock"
    assert detail["shortages"] == [{"component": material_id, "required": 6000, "available": 5000}]
    assert detail["run_id"]

    manufactured = client.post(
        "/app/manufacture",
        json={"recipe_id": recipe_id, "quantity_decimal": "2", "uom": "ea"},
    )
    assert manufactured.status_code == 200, manufactured.text
    assert manufactured.json()["run_id"]

    sale = client.post(
        "/app/stock/out",
        json={
            "item_id": product_id,
            "quantity_decimal": "1",
            "uom": "ea",
            "reason": "sold",
            "record_cash_event": True,
        },
    )
    assert sale.status_code == 200, sale.text
    assert sale.json().get("ok") is True

    summary = client.get("/app/finance/summary?from=2000-01-01&to=2100-01-01")
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["gross_sales_cents"] == 1000
    assert summary_payload["cogs_cents"] == 200
    assert summary_payload["gross_profit_cents"] == 800
    assert summary_payload["net_profit_cents"] == 300

    tx = client.get("/app/finance/transactions?from=2000-01-01&to=2100-01-01&limit=100")
    assert tx.status_code == 200, tx.text
    sale_rows = [row for row in tx.json()["transactions"] if row["kind"] == "sale"]
    assert sale_rows
    assert sale_rows[0]["amount_cents"] == 1000
    assert sale_rows[0]["cogs_cents"] == 200
    assert sale_rows[0]["gross_profit_cents"] == 800
