from __future__ import annotations
import os
from typing import Any, Dict, List, Tuple


def _b64u(s: str) -> str:
    import base64 as _b
    return _b.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _ub64u(s: str) -> str:
    import base64 as _b
    pad = "=" * (-len(s) % 4)
    return _b.urlsafe_b64decode(s + pad).decode()


class LocalFSProvider:
    """
    Core-owned local filesystem lister restricted to allow-listed roots.
    """

    def __init__(self, logger, settings_loader):
        self._log = logger("provider.local_fs")
        self._settings = settings_loader

    def _roots(self) -> List[str]:
        s = self._settings() or {}
        roots = s.get("local_roots", [])
        return [os.path.abspath(p) for p in roots if isinstance(p, str)]

    def status(self) -> Dict[str, Any]:
        return {"configured": bool(self._roots())}

    def list_children(self, *, parent_id: str) -> Dict[str, Any]:
        def mk_node(path: str) -> Dict[str, Any]:
            name = os.path.basename(path) or path
            try:
                is_dir = os.path.isdir(path)
                size = None if is_dir else os.path.getsize(path)
            except Exception:
                is_dir, size = False, None
            return {
                "source": "local_fs",
                "id": f"local:{_b64u(path)}",
                "parent_ids": [f"local:{_b64u(os.path.dirname(path))}"] if os.path.dirname(path) else [],
                "name": name,
                "type": "folder" if is_dir else "file",
                "mimeType": None,
                "has_children": is_dir,
                "size": size,
            }

        if parent_id == "local:root":
            return {"children": [mk_node(p) for p in self._roots()], "next_page_token": None}

        if parent_id.startswith("local:"):
            path = os.path.abspath(_ub64u(parent_id.split(":", 1)[1]))
            if not any(os.path.commonpath([path, r]) == r for r in self._roots()):
                return {"children": [], "next_page_token": None}
            try:
                entries = []
                with os.scandir(path) as it:
                    for e in it:
                        if e.is_symlink():
                            continue
                        entries.append(mk_node(os.path.join(path, e.name)))
                entries.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
                return {"children": entries, "next_page_token": None}
            except Exception:
                return {"children": [], "next_page_token": None}

        return {"children": [], "next_page_token": None}

    def stream_open(self, scope: str, recursive: bool, page_size: int) -> Dict[str, Any]:
        q = []
        if scope == "local_roots":
            for r in self._roots():
                q.append({"parent_id": f"local:{_b64u(r)}"})
        return {"scope": scope, "recursive": bool(recursive), "queue": q}

    def stream_next(
        self, cursor: Dict[str, Any], max_items: int
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], bool]:
        out: List[Dict[str, Any]] = []
        recursive = bool(cursor.get("recursive"))
        while len(out) < max_items and cursor["queue"]:
            head = cursor["queue"].pop(0)
            res = self.list_children(parent_id=head["parent_id"])
            children = res.get("children", [])
            out.extend(children)
            if recursive:
                for c in children:
                    if c.get("type") == "folder":
                        cursor["queue"].append({"parent_id": c["id"]})
        done = not cursor["queue"]
        return out, cursor, done

    def stream_close(self, cursor: Dict[str, Any]) -> None:
        return
