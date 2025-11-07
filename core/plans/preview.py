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

from typing import Any, Dict, Set, Tuple

from .model import Plan


def preview_plan(plan: Plan) -> Dict[str, Any]:
    stats: Dict[str, Any] = {"counts": {}, "collisions": [], "notes": []}
    for a in plan.actions:
        stats["counts"][a.kind.value] = stats["counts"].get(a.kind.value, 0) + 1
    seen: Set[Tuple[str, str]] = set()
    for a in plan.actions:
        dst_parent = a.meta.get("dst_parent_path") or a.dst_parent_id
        dst_name = a.meta.get("dst_name") or a.dst_name
        if dst_parent and dst_name:
            key = (str(dst_parent).lower(), str(dst_name).lower())
            if key in seen:
                stats["collisions"].append({"action_id": a.id, "reason": "dst_name_collision"})
            else:
                seen.add(key)
    return stats
