# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGDIR = ROOT / "plugins" / "violator"
PLUGDIR.mkdir(parents=True, exist_ok=True)
(PLUGDIR / "__init__.py").write_text("", encoding="utf-8")

(PLUGDIR / "plugin.py").write_text(
    "from core.contracts.plugin_v2 import PluginV2\n"
    "from core._internal import runtime  # forbidden\n"
    "class Plugin(PluginV2):\n"
    "    id='violator'; name='Violator'; version='0.0'; api_version='2'\n"
    "    def describe(self): return {'services':[], 'scopes':['read_base']}\n"
    "    def register_broker(self, b): pass\n",
    encoding="utf-8",
)


def test_discovery_rejects_internal_imports() -> None:
    if "core.plugins_alpha" in sys.modules:
        del sys.modules["core.plugins_alpha"]
    mod = importlib.import_module("core.plugins_alpha")
    plugs = mod.discover_alpha_plugins()
    ids = [getattr(p, "id", "unknown") for p in plugs]
    assert "violator" not in ids


def teardown_module(module) -> None:  # type: ignore[override]
    if PLUGDIR.exists():
        shutil.rmtree(PLUGDIR)
