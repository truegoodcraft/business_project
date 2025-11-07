# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import argparse
import importlib
import json
import sys
from typing import Any, Dict

from core.contracts.plugin_v2 import PluginV2


def _load_plugin(plugin_id: str) -> PluginV2:
    module_names = [f"plugins.{plugin_id}.plugin", f"plugins.{plugin_id}"]
    last_exc: Exception | None = None
    for name in module_names:
        try:
            module = importlib.import_module(name)
        except Exception as exc:  # pragma: no cover - defensive
            last_exc = exc
            continue
        plugin_cls = getattr(module, "Plugin", None)
        if plugin_cls and issubclass(plugin_cls, PluginV2):
            return plugin_cls()
    raise RuntimeError(f"plugin_not_found:{plugin_id}:{last_exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sandbox runner")
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--fn", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(sys.stdin.read() or "{}")
    plugin = _load_plugin(args.plugin)
    input_data: Dict[str, Any] = payload.get("input") or {}
    limits = payload.get("limits") or {}
    proposal = plugin.plan_transform(args.fn, input_data, limits=limits)
    output = {"proposal": proposal}
    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
