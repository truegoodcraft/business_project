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
import base64
import ntpath
import os
from typing import Any, Dict, List, Tuple


def _is_windows_path(path: str) -> bool:
    return bool(path) and (
        path.startswith(("\\\\", "//")) or (len(path) >= 2 and path[1] == ":")
    )


def _norm(path: str) -> str:
    if _is_windows_path(path):
        return ntpath.normcase(ntpath.normpath(ntpath.abspath(path)))
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _drive_id(path: str) -> str:
    splitter = ntpath if _is_windows_path(path) else os.path
    drive = splitter.splitdrive(path)[0]
    if drive:
        return drive.lower()
    if len(path) >= 2 and path[1] == ":":
        return path[:2].lower()
    return ""


def _same_drive(a: str, b: str) -> bool:
    da, db = _drive_id(a), _drive_id(b)
    if da or db:
        return da == db
    return True


def _is_under_root(path: str, root: str) -> bool:
    ap, rp = _norm(path), _norm(root)
    if not _same_drive(ap, rp):
        return False
    try:
        common = (
            ntpath.commonpath([ap, rp])
            if _is_windows_path(path) or _is_windows_path(root)
            else os.path.commonpath([ap, rp])
        )
        return common == rp
    except Exception:
        trimmed = rp.rstrip("\\/")
        if not trimmed:
            return ap == rp
        sep = "\\" if ("\\" in trimmed or _is_windows_path(rp)) else os.sep
        return ap == rp or ap.startswith(trimmed + sep)


def _b64u(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _ub64u(s: str) -> str:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad).decode()


class LocalFSProvider:
    """Core-owned local filesystem lister restricted to allow-listed roots."""

    def __init__(self, logger_factory, settings_loader):
        self._log = logger_factory("provider.local_fs")
        self._settings_loader = settings_loader

    def _settings(self) -> Dict[str, Any]:
        try:
            raw = self._settings_loader() or {}
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _roots(self) -> List[str]:
        settings = self._settings()
        roots = settings.get("local_roots", []) if isinstance(settings, dict) else []
        return [_norm(p) for p in roots if isinstance(p, str)]

    def status(self) -> Dict[str, Any]:
        roots = self._roots()
        return {"configured": bool(roots), "roots": roots}

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
            decoded = _ub64u(parent_id.split(":", 1)[1])
            path = (
                ntpath.abspath(decoded)
                if _is_windows_path(decoded)
                else os.path.abspath(decoded)
            )
            if not any(_is_under_root(path, r) for r in self._roots()):
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
