# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import sys
import types

import pytest

from tests.conftest import reset_bus_modules

pytestmark = pytest.mark.unit


def _effective_routes(app):
    for route in app.routes:
        iter_contexts = getattr(route, "effective_route_contexts", None)
        if callable(iter_contexts):
            yield from iter_contexts()
        else:
            yield route


def test_reset_bus_modules_removes_parent_package_child_reference(monkeypatch):
    package = types.ModuleType("fixture_reset_package")
    child = types.ModuleType("fixture_reset_package.child")
    package.child = child
    monkeypatch.setitem(sys.modules, "fixture_reset_package", package)
    monkeypatch.setitem(sys.modules, "fixture_reset_package.child", child)

    reset_bus_modules(["fixture_reset_package.child"])

    assert "fixture_reset_package.child" not in sys.modules
    assert not hasattr(package, "child")


def test_reset_bus_modules_removes_orphaned_parent_reference(monkeypatch):
    package = types.ModuleType("fixture_orphan_package")
    child = types.ModuleType("fixture_orphan_package.child")
    package.child = child
    monkeypatch.setitem(sys.modules, "fixture_orphan_package", package)
    monkeypatch.delitem(sys.modules, "fixture_orphan_package.child", raising=False)

    reset_bus_modules(["fixture_orphan_package.child"])

    assert not hasattr(package, "child")


def test_reset_bus_modules_removes_mismatched_stale_parent_reference(monkeypatch):
    package = types.ModuleType("fixture_stale_package")
    current_child = types.ModuleType("fixture_stale_package.child")
    stale_child = types.ModuleType("fixture_stale_package.child")
    package.child = stale_child
    monkeypatch.setitem(sys.modules, "fixture_stale_package", package)
    monkeypatch.setitem(sys.modules, "fixture_stale_package.child", current_child)

    reset_bus_modules(["fixture_stale_package.child"])

    assert "fixture_stale_package.child" not in sys.modules
    assert not hasattr(package, "child")


def test_repeated_isolated_clients_share_one_model_graph_and_fresh_schema(bus_client_factory):
    observed_bases = []
    observed_db_paths = []
    observed_item_endpoints = []

    for label in ("first", "second"):
        with bus_client_factory(label) as env:
            observed_bases.append((env["api_http"].Base, env["models"].Base))
            observed_db_paths.append(env["db_path"])
            assert env["api_http"].Base is env["models"].Base
            assert env["client"].get("/health").status_code == 200
            assert "document_sequences" in env["models"].Base.metadata.tables
            effective_routes = list(_effective_routes(env["api_http"].APP))
            route_snapshot = [
                (
                    type(route).__name__,
                    getattr(route, "path", None),
                    sorted(getattr(route, "methods", None) or set()),
                    getattr(getattr(route, "endpoint", None), "__module__", None),
                )
                for route in effective_routes
            ]
            item_routes = [
                route
                for route in effective_routes
                if getattr(route, "path", None) == "/app/items"
                and "POST" in (getattr(route, "methods", None) or set())
            ]
            assert item_routes, route_snapshot
            item_endpoint = item_routes[0].endpoint
            observed_item_endpoints.append(item_endpoint)
            assert item_endpoint.__globals__["Item"] is env["models"].Item
            assert item_endpoint.__globals__["get_session"] is env["engine"].get_session

            with env["engine"].get_engine().connect() as connection:
                table_names = {
                    str(row[0])
                    for row in connection.exec_driver_sql(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            assert {"vendors", "document_sequences"} <= table_names

    assert all(api_base is model_base for api_base, model_base in observed_bases)
    assert observed_db_paths[0] != observed_db_paths[1]
    assert all(path.exists() for path in observed_db_paths)
    assert observed_item_endpoints[0] is not observed_item_endpoints[1]
