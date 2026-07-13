# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import sys
import types

import pytest

from tests.conftest import reset_bus_modules

pytestmark = pytest.mark.unit


def test_reset_bus_modules_removes_parent_package_child_reference(monkeypatch):
    package = types.ModuleType("fixture_reset_package")
    child = types.ModuleType("fixture_reset_package.child")
    package.child = child
    monkeypatch.setitem(sys.modules, "fixture_reset_package", package)
    monkeypatch.setitem(sys.modules, "fixture_reset_package.child", child)

    reset_bus_modules(["fixture_reset_package.child"])

    assert "fixture_reset_package.child" not in sys.modules
    assert not hasattr(package, "child")
