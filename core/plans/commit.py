import os
import shutil
from typing import Any, Dict, List

from send2trash import send2trash

from .model import ActionKind, Plan


def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _same_volume(a: str, b: str) -> bool:
    try:
        return os.path.splitdrive(a)[0].lower() == os.path.splitdrive(b)[0].lower()
    except Exception:
        return False


def _move(src: str, dst: str):
    _ensure_parent(dst)
    if _same_volume(src, dst):
        os.replace(src, dst)
    else:
        shutil.move(src, dst)


def _copy(src: str, dst: str):
    _ensure_parent(dst)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _delete(path: str):
    if os.path.exists(path):
        send2trash(path)


def _hardlink(src: str, dst: str):
    _ensure_parent(dst)
    os.link(src, dst)


def commit_local(plan: Plan) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for a in plan.actions:
        try:
            src = a.meta.get("src_path")
            dst = a.meta.get("dst_path")
            if not dst:
                parent = a.meta.get("dst_parent_path")
                name = a.meta.get("dst_name") or a.dst_name
                if parent and name:
                    dst = os.path.join(parent, name)
            if a.kind == ActionKind.DELETE:
                if not src:
                    raise ValueError("DELETE requires meta.src_path")
                _delete(src)
            elif a.kind in (ActionKind.MOVE, ActionKind.RENAME):
                if not (src and dst):
                    raise ValueError("MOVE/RENAME require src_path and dst_path/dst_*")
                _move(src, dst)
            elif a.kind == ActionKind.COPY:
                if not (src and dst):
                    raise ValueError("COPY requires src_path and dst_path/dst_*")
                _copy(src, dst)
            elif a.kind == ActionKind.HARDLINK:
                if not (src and dst):
                    raise ValueError("HARDLINK requires src_path and dst_path/dst_*")
                _hardlink(src, dst)
            else:
                raise ValueError(f"Unsupported action kind: {a.kind}")
            results.append({"action_id": a.id, "status": "ok"})
        except Exception as e:  # pragma: no cover - error paths
            results.append({"action_id": a.id, "status": "error", "error": str(e)})
    return {"ok": all(r["status"] == "ok" for r in results), "results": results}
