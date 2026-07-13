from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient


def _create_contact(bus_client, name: str = "Acme Customer") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        contact = models.Vendor(name=name, role="contact", is_vendor=0)
        db.add(contact)
        db.commit()
        return int(contact.id)


def _create_item(bus_client, name: str = "Widget", *, dimension: str = "count", uom: str = "ea") -> int:
    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        item = models.Item(name=name, dimension=dimension, uom=uom, qty_stored=0, is_product=True)
        db.add(item)
        db.commit()
        return int(item.id)


def _create_job(client, **payload) -> dict:
    body = {"title": "Launch batch"}
    body.update(payload)
    response = client.post("/app/jobs", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _authority_counts(bus_client) -> dict[str, int]:
    models = bus_client["models"]
    recipes = bus_client["recipes"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        return {
            "item_movements": db.query(models.ItemMovement).count(),
            "item_batches": db.query(models.ItemBatch).count(),
            "manufacturing_runs": db.query(recipes.ManufacturingRun).count(),
            "cash_events": db.query(models.CashEvent).count(),
        }


def test_job_crud_defaults_filters_and_invalid_inputs(bus_client):
    client = bus_client["client"]
    contact_id = _create_contact(bus_client)

    created = _create_job(client, contact_id=contact_id, priority=4, notes="rush")

    assert created["status"] == "draft"
    assert created["contact_id"] == contact_id
    assert created["line_count"] == 0
    assert created["estimated_value_cents"] == 0
    assert created["contact_display"] == "Acme Customer"
    assert [event["event_type"] for event in created["events"]] == ["job.created"]

    listed = client.get("/app/jobs", params={"status": "draft", "contact_id": contact_id, "q": "Launch"})
    assert listed.status_code == 200, listed.text
    assert [job["id"] for job in listed.json()] == [created["id"]]

    detail = client.get(f"/app/jobs/{created['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["notes"] == "rush"

    updated = client.patch(f"/app/jobs/{created['id']}", json={"title": "Launch batch revised", "priority": 7})
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Launch batch revised"
    assert updated.json()["priority"] == 7

    invalid_status = client.post("/app/jobs", json={"title": "Bad", "status": "shipped"})
    assert invalid_status.status_code == 400

    invalid_contact = client.post("/app/jobs", json={"title": "Bad", "contact_id": 999999})
    assert invalid_contact.status_code == 404


def test_status_transition_only_changes_jobs_and_events(bus_client):
    client = bus_client["client"]
    job = _create_job(client)
    before = _authority_counts(bus_client)

    done = client.post(f"/app/jobs/{job['id']}/status", json={"status": "done"})

    assert done.status_code == 200, done.text
    assert done.json()["status"] == "done"
    assert done.json()["closed_at"] is not None
    assert before == _authority_counts(bus_client)
    assert "job.status_changed" in [event["event_type"] for event in done.json()["events"]]

    active = client.post(f"/app/jobs/{job['id']}/status", json={"status": "active"})
    assert active.status_code == 200, active.text
    assert active.json()["status"] == "active"
    assert active.json()["closed_at"] is None
    assert before == _authority_counts(bus_client)


def test_draft_jobs_and_lines_do_not_touch_authority_tables(bus_client):
    client = bus_client["client"]
    item_id = _create_item(bus_client)
    job = _create_job(client)
    before = _authority_counts(bus_client)

    line = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Two widgets",
            "item_id": item_id,
            "quantity_decimal": "2",
            "uom": "ea",
            "unit_price_cents": 1200,
        },
    )

    assert line.status_code == 200, line.text
    assert line.json()["qty_base"] == 2000
    assert before == _authority_counts(bus_client)

    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        assert db.get(models.Item, item_id).qty_stored == 0


def test_job_line_quantity_authority_is_qty_base_only(bus_client):
    client = bus_client["client"]
    item_id = _create_item(bus_client, name="Flour", dimension="weight", uom="kg")
    job = _create_job(client)

    response = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Flour bag",
            "item_id": item_id,
            "quantity_decimal": "1.5",
            "uom": "kg",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["qty_base"] == 1_500_000
    assert payload["display_uom"] == "kg"
    assert "qty_decimal" not in payload
    assert "quantity_decimal" not in payload

    jobs = bus_client["jobs"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        line = db.get(jobs.JobLine, payload["id"])
        assert isinstance(line.qty_base, int)
        assert line.qty_base == 1_500_000
        assert "qty_decimal" not in line.__table__.columns
        assert "quantity_decimal" not in line.__table__.columns

    rejected = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={"line_type": "product", "description": "bad", "item_id": item_id, "qty_base": 12},
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["error"] == "legacy_quantity_keys_forbidden"


def test_service_line_quantity_allows_ea_without_item_or_recipe(bus_client):
    client = bus_client["client"]
    job = _create_job(client)
    before = _authority_counts(bus_client)

    response = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "service",
            "description": "Consulting hour",
            "quantity_decimal": "1",
            "uom": "ea",
            "unit_price_cents": 5000,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["qty_base"] == 1000
    assert payload["display_uom"] == "ea"
    assert payload["item_id"] is None
    assert payload["recipe_id"] is None
    assert before == _authority_counts(bus_client)


def test_job_line_quantity_rejects_invalid_or_missing_uom_with_stable_codes(bus_client):
    client = bus_client["client"]
    item_id = _create_item(bus_client)
    job = _create_job(client)

    invalid_uom = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Bad unit",
            "item_id": item_id,
            "quantity_decimal": "1",
            "uom": "1",
        },
    )
    assert invalid_uom.status_code == 400
    assert invalid_uom.json()["detail"] == {
        "error": "bad_request",
        "message": "invalid_uom",
    }

    missing_uom = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Missing unit",
            "item_id": item_id,
            "quantity_decimal": "1",
        },
    )
    assert missing_uom.status_code == 400
    assert missing_uom.json()["detail"] == {
        "error": "bad_request",
        "message": "uom_required",
    }


def test_manual_job_events_are_reference_only(bus_client):
    client = bus_client["client"]
    item_id = _create_item(bus_client)
    job = _create_job(client)

    models = bus_client["models"]
    engine = bus_client["engine"]
    with engine.SessionLocal() as db:
        movement = models.ItemMovement(item_id=item_id, qty_change=0, source_kind="test", source_id="move-1")
        db.add(movement)
        db.commit()
        movement_id = int(movement.id)
        before_count = db.query(models.ItemMovement).count()

    event = client.post(
        f"/app/jobs/{job['id']}/events",
        json={
            "event_type": "manual.note",
            "message": "Linked for memory only.",
            "source_kind": "item_movement",
            "source_id": str(movement_id),
            "meta": {"observed": True},
        },
    )

    assert event.status_code == 200, event.text
    assert event.json()["source_kind"] == "item_movement"
    assert event.json()["source_id"] == str(movement_id)
    assert json.loads(event.json()["meta"]) == {"observed": True}
    with engine.SessionLocal() as db:
        assert db.query(models.ItemMovement).count() == before_count
        assert db.get(models.ItemMovement, movement_id).source_id == "move-1"


def test_cancelled_jobs_have_no_future_execution_placeholders(bus_client):
    client = bus_client["client"]
    item_id = _create_item(bus_client)
    job = _create_job(client)
    line = client.post(
        f"/app/jobs/{job['id']}/lines",
        json={
            "line_type": "product",
            "description": "Cancelled line",
            "item_id": item_id,
            "quantity_decimal": "1",
            "uom": "ea",
        },
    ).json()
    before = _authority_counts(bus_client)

    cancelled = client.post(f"/app/jobs/{job['id']}/status", json={"status": "cancelled"})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["closed_at"] is not None

    manufacture = client.post(f"/app/jobs/{job['id']}/lines/{line['id']}/manufacture", json={})
    deliver = client.post(f"/app/jobs/{job['id']}/lines/{line['id']}/deliver", json={})

    assert manufacture.status_code == 404
    assert deliver.status_code == 404
    assert before == _authority_counts(bus_client)


def test_job_routes_require_auth_and_write_gate_but_reads_survive_read_only(bus_client):
    client = bus_client["client"]
    job = _create_job(client)
    anonymous = TestClient(bus_client["api_http"].APP)

    assert anonymous.get("/app/jobs").status_code == 401

    api_http = bus_client["api_http"]
    api_http.app.state.allow_writes = False
    read = client.get(f"/app/jobs/{job['id']}")
    write = client.post("/app/jobs", json={"title": "Blocked"})

    assert read.status_code == 200, read.text
    assert write.status_code == 403, write.text
    assert write.json()["detail"]["error"] == "writes_disabled"


def test_jobs_schema_is_forward_only_empty_additive_tables(bus_client, bus_db_path):
    bus_client["api_http"].startup_migrations()

    with sqlite3.connect(bus_db_path) as con:
        tables = {
            row[0]
            for row in con.execute(
                "select name from sqlite_master where type='table' and name in ('jobs','job_lines','job_events')"
            )
        }
        counts = {table: con.execute(f"select count(*) from {table}").fetchone()[0] for table in tables}
        item_columns = {row[1] for row in con.execute("pragma table_info(items)")}
        run_columns = {row[1] for row in con.execute("pragma table_info(manufacturing_runs)")}

    assert tables == {"jobs", "job_lines", "job_events"}
    assert counts == {"jobs": 0, "job_lines": 0, "job_events": 0}
    assert "job_id" not in item_columns
    assert "job_id" not in run_columns
