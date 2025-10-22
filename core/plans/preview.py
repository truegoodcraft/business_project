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
