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

import json
import pathlib
import os


def validate_plugin_config(plugin: str) -> list[str]:
    problems = []
    p = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if not p.exists():
        problems.append(f"{plugin}: missing config.schema.json")
        return problems
    schema = json.loads(p.read_text())
    for key in schema.get("env", []):
        if not os.getenv(key):
            problems.append(f"{plugin}: missing env {key}")
    return problems
