import importlib
import json
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def inventory_journal_setup(tmp_path, monkeypatch):
    db_path = tmp_path / "app.db"
    journal_path = tmp_path / "journals" / "inventory.jsonl"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("BUS_INVENTORY_JOURNAL", str(journal_path))

    for module_name in [
        "core.api.http",
        "core.api.routes.ledger_api",
        "core.appdb.engine",
        "core.appdb.ledger",
        "core.appdb.models",
        "core.journal.inventory",
        "core.ledger.fifo",
        "core.services.models",
    ]:
        sys.modules.pop(module_name, None)

    import core.appdb.engine as engine_module
    import core.appdb.ledger as ledger_module
    import core.appdb.models as models_module
    import core.api.http as api_http
    import core.api.routes.ledger_api as ledger_api
    import core.journal.inventory as inventory_journal
    import core.ledger.fifo as fifo_module
    import core.services.models as services_models

    engine_module = importlib.reload(engine_module)
    ledger_module = importlib.reload(ledger_module)
    models_module = importlib.reload(models_module)
    api_http = importlib.reload(api_http)
    ledger_api = importlib.reload(ledger_api)
    inventory_journal = importlib.reload(inventory_journal)
    fifo_module = importlib.reload(fifo_module)
    services_models = importlib.reload(services_models)

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
        item = models_module.Item(name="Widget", uom="ea", qty_stored=0)
        db.add(item)
        db.commit()
        item_id = item.id

    yield {
        "client": client,
        "engine": engine_module,
        "models": models_module,
        "ledger_api": ledger_api,
        "journal_path": journal_path,
        "item_id": item_id,
    }


def test_purchase_appends_journal(inventory_journal_setup):
    client = inventory_journal_setup["client"]
    engine = inventory_journal_setup["engine"]
    models = inventory_journal_setup["models"]
    journal_path = inventory_journal_setup["journal_path"]

    resp = client.post(
        "/app/ledger/purchase",
        json={
            "item_id": inventory_journal_setup["item_id"],
            "qty": 3,
            "unit_cost_cents": 125,
            "source_kind": "purchase",
            "source_id": "po-1",
        },
    )

    assert resp.status_code == 200, resp.text
    assert resp.json().get("ok") is True

    with engine.SessionLocal() as db:
        batches = db.query(models.ItemBatch).all()
        assert len(batches) == 1
        assert batches[0].qty_initial == pytest.approx(3)

    assert journal_path.exists()
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["op"] == "purchase"
    assert entry["qty"] == pytest.approx(3)
    assert entry["unit_cost_cents"] == 125
    assert entry["item_id"] == inventory_journal_setup["item_id"]
    assert entry["batch_id"] == resp.json().get("batch_id")


def test_journal_failure_does_not_block_adjustment(inventory_journal_setup, monkeypatch):
    client = inventory_journal_setup["client"]
    engine = inventory_journal_setup["engine"]
    models = inventory_journal_setup["models"]
    journal_path = inventory_journal_setup["journal_path"]

    def boom(_entry):
        raise RuntimeError("fsync failed")

    monkeypatch.setattr("core.api.routes.ledger_api.append_inventory", boom)

    resp = client.post(
        "/app/ledger/adjust",
        json={"item_id": inventory_journal_setup["item_id"], "qty_change": 2},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}

    with engine.SessionLocal() as db:
        batches = db.query(models.ItemBatch).all()
        assert len(batches) == 1
        assert batches[0].qty_initial == pytest.approx(2)
        assert batches[0].qty_remaining == pytest.approx(2)

    # Journal write failed but DB state is still committed
    assert not journal_path.exists()
