import os, shutil
from typing import Any, Dict, List

try:
    from send2trash import send2trash
except Exception as _e:
    def send2trash(_path: str):
        raise RuntimeError("Send2Trash is not installed. Install with: python -m pip install Send2Trash==1.8.2") from _e

from .model import Plan, ActionKind
from core.reader.ids import rid_to_path
from core.reader.roots import get_allowed_local_roots


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


def _under_roots(path: str, roots: List[str]) -> bool:
    import os

    abs_path = os.path.normcase(os.path.abspath(path))
    for root in roots or []:
        abs_root = os.path.normcase(os.path.abspath(root))
        try:
            if os.path.commonpath([abs_path, abs_root]) == abs_root:
                return True
        except Exception:
            # Different drives on Windows may raise ValueError.
            pass
    return False


def commit_local(plan: Plan) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    roots = get_allowed_local_roots()
    for a in plan.actions:
        try:
            src = a.meta.get("src_path")
            dst = a.meta.get("dst_path")
            parent = a.meta.get("dst_parent_path")

            if getattr(a, "src_id", None) and not src:
                src = rid_to_path(a.src_id, roots)
            if getattr(a, "dst_parent_id", None) and not parent:
                parent = rid_to_path(a.dst_parent_id, roots)

            if not dst and parent:
                name = a.meta.get("dst_name") or a.dst_name
                if parent and name:
                    dst = os.path.join(parent, name)

            if src and not _under_roots(src, roots):
                raise ValueError("out_of_scope: src")
            if dst and not _under_roots(dst, roots):
                raise ValueError("out_of_scope: dst")
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
