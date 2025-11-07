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

import os
import json
import pathlib


def load_core_config() -> dict:
    return {}


def load_plugin_config(plugin: str) -> dict:
    base = {}
    schema = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if schema.exists():
        base = json.loads(schema.read_text())
    out = {}
    for k in base.get("env", []):
        v = os.getenv(k)
        if v is not None:
            out[k] = v
    return out


def plugin_env_whitelist(plugin: str) -> list[str]:
    """Return env keys this plugin is allowed to see (from its config.schema.json)."""
    schema = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if not schema.exists():
        return []
    data = json.loads(schema.read_text())
    return list(data.get("env", []))
