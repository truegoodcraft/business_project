# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest

# Ensure local packages are importable and all collection-time runtime state is
# confined to a generated workspace directory. Some test modules import the API
# during collection, before fixture setup can redirect AppData and logging.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PYTEST_SESSION_ROOT = Path(tempfile.mkdtemp(prefix=".gate-pytest-", dir=ROOT))
_PYTEST_TEMP_ROOT = _PYTEST_SESSION_ROOT / "pytest-temp"
_PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["PYTEST_DEBUG_TEMPROOT"] = str(_PYTEST_TEMP_ROOT)
os.environ["LOCALAPPDATA"] = str(_PYTEST_SESSION_ROOT / "LocalAppData")
os.environ["BUSCORE_HOME"] = str(_PYTEST_SESSION_ROOT / "BusCoreHome")
os.environ["BUS_DB"] = str(_PYTEST_SESSION_ROOT / "collection.db")
_SESSION_INVENTORY_JOURNAL = str(_PYTEST_SESSION_ROOT / "journals" / "inventory.jsonl")
_SESSION_MANUFACTURING_JOURNAL = str(_PYTEST_SESSION_ROOT / "journals" / "manufacturing.jsonl")
os.environ["BUS_INVENTORY_JOURNAL"] = _SESSION_INVENTORY_JOURNAL
os.environ["BUS_MANUFACTURING_JOURNAL"] = _SESSION_MANUFACTURING_JOURNAL
os.environ["BUS_DISABLE_INDEX"] = "1"
os.environ["BUS_DEV"] = "0"


BUS_MODULES_TO_RESET = [
    "core.api.http",
    "core.api.routes.auth",
    "core.api.routes.config",
    "core.api.routes.dev",
    "core.api.routes.dev_dbinfo",
    "core.api.routes.finance_api",
    "core.api.routes.invoices",
    "core.api.routes.items",
    "core.api.routes.jobs",
    "core.api.routes.ledger_api",
    "core.api.routes.logs_api",
    "core.api.routes.manufacturing",
    "core.api.routes.recipes",
    "core.api.routes.system_state",
    "core.api.routes.telemetry",
    "core.api.routes.transactions",
    "core.api.routes.update",
    "core.api.routes.users",
    "core.api.routes.vendors",
    "core.appdata.paths",
    "core.appdb.engine",
    "core.appdb.ledger",
    "core.appdb.migrate",
    "core.appdb.models",
    "core.appdb.models_auth",
    "core.appdb.models_invoices",
    "core.appdb.models_jobs",
    "core.appdb.models_recipes",
    "core.appdb.paths",
    "core.appdb.session",
    "core.appdb.sqlite_patch",
    "core.auth.audit",
    "core.auth.dependencies",
    "core.auth.google_sa",
    "core.auth.management",
    "core.auth.passwords",
    "core.auth.permissions",
    "core.auth.sessions",
    "core.auth.store",
    "core.config.manager",
    "core.config.paths",
    "core.config.writes",
    "core.journal.inventory",
    "core.journal.manufacturing",
    "core.manufacturing.service",
    "core.policy.store",
    "core.runtime.instance_lock",
    "core.services.invoices",
    "core.services.jobs",
    "core.services.models",
    "core.services.stock_mutation",
    "core.services.update",
    "core.telemetry",
    "core.telemetry.client",
    "tgc.bootstrap_fs",
    "tgc.logging_setup",
    "tgc.platform_adapters",
    "tgc.security",
    "tgc.settings",
    "tgc.state",
    "tgc.tokens",
]


def reset_bus_modules(module_names: list[str]) -> None:
    """Remove cached runtime modules and their package attributes coherently."""

    for module_name in sorted(module_names, key=lambda value: value.count("."), reverse=True):
        module = sys.modules.pop(module_name, None)
        parent_name, separator, child_name = module_name.rpartition(".")
        if not separator:
            continue
        parent = sys.modules.get(parent_name)
        if parent is None:
            continue
        child = getattr(parent, child_name, None)
        if (module is not None and child is module) or getattr(child, "__name__", None) == module_name:
            delattr(parent, child_name)


def _close_bus_logger() -> None:
    logger = logging.getLogger("tgc.buscore")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def _requested_bus_dev(request: pytest.FixtureRequest) -> str:
    marker = request.node.get_closest_marker("bus_dev")
    if marker and marker.args:
        return str(marker.args[0])
    if hasattr(request, "param"):
        return str(request.param)
    # The shared API fixture is production-mode by default regardless of the
    # developer's shell. Tests that exercise dev behavior opt in explicitly.
    return "0"


@contextmanager
def _isolated_bus_client(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    bus_dev: str,
) -> Iterator[dict]:
    db_path = root / "app.db"
    local_app_data = root / "LocalAppData"
    monkeypatch.setenv("BUS_DB", str(db_path))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("BUSCORE_HOME", str(root / "BusCoreHome"))
    monkeypatch.setenv("BUS_DEV", bus_dev)
    monkeypatch.setenv("BUS_DISABLE_INDEX", "1")
    inventory_journal = os.environ.get("BUS_INVENTORY_JOURNAL")
    if not inventory_journal or inventory_journal == _SESSION_INVENTORY_JOURNAL:
        inventory_journal = str(root / "journals" / "inventory.jsonl")
    manufacturing_journal = os.environ.get("BUS_MANUFACTURING_JOURNAL")
    if not manufacturing_journal or manufacturing_journal == _SESSION_MANUFACTURING_JOURNAL:
        manufacturing_journal = str(root / "journals" / "manufacturing.jsonl")
    monkeypatch.setenv("BUS_INVENTORY_JOURNAL", inventory_journal)
    monkeypatch.setenv("BUS_MANUFACTURING_JOURNAL", manufacturing_journal)

    _close_bus_logger()
    reset_bus_modules(BUS_MODULES_TO_RESET)

    # Import the application once, after environment setup. All model, route,
    # service, and engine references therefore belong to one module graph.
    import core.api.http as api_http
    import core.appdb.engine as engine_module
    import core.appdb.ledger as ledger_module
    import core.appdb.models as models_module
    import core.appdb.models_invoices as invoices_module
    import core.appdb.models_jobs as jobs_module
    import core.appdb.models_recipes as recipes_module
    import core.services.invoices as invoice_service_module
    from core.config.writes import set_writes_enabled
    from fastapi.testclient import TestClient
    from sqlalchemy import event

    assert api_http.Base is models_module.Base

    # The fixture still runs the production lifespan and canonical SQLite
    # schema path. Disable only physical fsync for generated test databases so
    # hundreds of isolated DDL bootstraps do not turn the serial gate into a
    # disk-latency benchmark; SQL transaction behavior and constraints remain.
    fixture_engine = engine_module.get_engine()

    def _fast_test_sqlite(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA synchronous=OFF")
        dbapi_connection.execute("PRAGMA temp_store=MEMORY")

    event.listen(fixture_engine, "connect", _fast_test_sqlite)

    set_writes_enabled(True)
    try:
        with TestClient(api_http.APP) as client:
            session_token = api_http._load_or_create_token()
            api_http.app.state.app_state.tokens._rec.token = session_token
            client.headers.update({"Cookie": f"bus_session={session_token}"})

            yield {
                "client": client,
                "engine": engine_module,
                "models": models_module,
                "api_http": api_http,
                "jobs": jobs_module,
                "invoices": invoices_module,
                "invoice_service": invoice_service_module,
                "recipes": recipes_module,
                "ledger": ledger_module,
                "local_app_data": local_app_data,
                "db_path": db_path,
            }
    finally:
        set_writes_enabled(False)
        api_http.app.state.allow_writes = False
        engine_module.dispose_engine()
        _close_bus_logger()


@pytest.fixture()
def bus_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("BUS_DB", str(db_path))
    return db_path


@pytest.fixture()
def bus_client_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
):
    counter = 0

    def _factory(label: str | None = None, *, bus_dev: str | None = None):
        nonlocal counter
        counter += 1
        client_root = tmp_path / (label or f"client-{counter}")
        return _isolated_bus_client(
            client_root,
            monkeypatch,
            bus_dev=bus_dev if bus_dev is not None else _requested_bus_dev(request),
        )

    return _factory


@pytest.fixture()
def bus_client(bus_client_factory, request: pytest.FixtureRequest):
    # Indirect parametrization targets this fixture, not bus_client_factory, so
    # forward the requested development mode explicitly to the shared factory.
    with bus_client_factory("default", bus_dev=_requested_bus_dev(request)) as env:
        yield env


def pytest_sessionfinish(session, exitstatus) -> None:
    _close_bus_logger()
    shutil.rmtree(_PYTEST_SESSION_ROOT, ignore_errors=True)
