"""
Reader plugin: multi-source read-only catalog (Drive + Local MVP).
Capabilities: catalog.list, catalog.search
"""
from __future__ import annotations

import base64
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

SERVICE_ID = "reader"
VERSION = "0.1.0"

_broker = None
_log = None


# ---- utils

def _b64u(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _ub64u(value: str) -> str:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad).decode()


def _settings() -> Dict[str, Any]:
    return {
        "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
        "local_roots": [],
    }


# ---- Google auth helpers (read-only)

def _google_client() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    cid = (
        _broker.get_secret("google", "client_id")
        or _broker.get_secret("google_oauth", "client_id")
    )
    cs = (
        _broker.get_secret("google", "client_secret")
        or _broker.get_secret("google_oauth", "client_secret")
    )
    rt = _broker.get_secret("google_drive", "refresh_token")
    return cid, cs, rt


def _google_access_token() -> Optional[str]:
    if _broker is None:
        return None
    cid, cs, rt = _google_client()
    if not (cid and cs and rt):
        return None
    session = _broker.http_session(SERVICE_ID)
    response = session.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": cid,
            "client_secret": cs,
            "grant_type": "refresh_token",
            "refresh_token": rt,
        },
        timeout=6,
    )
    if response.status_code != 200:
        return None
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    return payload.get("access_token")


# ---- Source: Drive

def _drive_children(params: Dict[str, Any]) -> Dict[str, Any]:
    token = _google_access_token()
    if not token:
        return {"children": [], "next_page_token": None}

    parent_id = params.get("parent_id", "drive:root")
    page_size = int(params.get("page_size", 200))
    page_token = params.get("page_token")
    session = _broker.http_session("reader.drive")
    session.headers.update({"Authorization": f"Bearer {token}"})

    def _files_list(query: str, corpora: str = "allDrives", drive_id: Optional[str] = None):
        base = "https://www.googleapis.com/drive/v3/files"
        request_params = {
            "q": query,
            "fields": "nextPageToken,files(id,name,mimeType,parents,driveId,shortcutDetails,modifiedTime,size)",
            "includeItemsFromAllDrives": "true",
            "supportsAllDrives": "true",
            "corpora": corpora,
            "pageSize": page_size,
        }
        if page_token:
            request_params["pageToken"] = page_token
        if drive_id:
            request_params["driveId"] = drive_id
        url = f"{base}?{urllib.parse.urlencode(request_params)}"
        response = session.get(url, timeout=8)
        response.raise_for_status()
        return response.json()

    def _node(obj: Dict[str, Any]) -> Dict[str, Any]:
        mime = obj.get("mimeType", "")
        is_folder = mime == "application/vnd.google-apps.folder"
        is_shortcut = mime == "application/vnd.google-apps.shortcut"
        node_id = f"drive:{obj['id']}"
        size_raw = obj.get("size")
        try:
            size_value = int(size_raw) if size_raw is not None else None
        except (TypeError, ValueError):
            size_value = None
        return {
            "id": node_id,
            "name": obj.get("name", obj["id"]),
            "type": "folder" if is_folder else ("shortcut" if is_shortcut else "file"),
            "mimeType": mime,
            "has_children": bool(is_folder or is_shortcut),
            "modifiedTime": obj.get("modifiedTime"),
            "size": size_value,
            "driveId": obj.get("driveId"),
        }

    if parent_id == "drive:shared":
        response = session.get(
            "https://www.googleapis.com/drive/v3/drives?fields=nextPageToken,drives(id,name)&pageSize=100",
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        drives = payload.get("drives", []) if isinstance(payload, dict) else []
        children = [
            {
                "id": f"drive:drive/{drive['id']}:root",
                "name": drive.get("name", drive.get("id")),
                "type": "folder",
                "mimeType": "application/vnd.google-apps.folder",
                "has_children": True,
                "driveId": drive.get("id"),
            }
            for drive in drives
            if isinstance(drive, dict) and drive.get("id")
        ]
        return {"children": children, "next_page_token": payload.get("nextPageToken") if isinstance(payload, dict) else None}

    if parent_id == "drive:root":
        data = _files_list("'root' in parents and trashed=false")
        files = data.get("files", []) if isinstance(data, dict) else []
        children = [
            {
                "id": "drive:shared",
                "name": "Shared drives",
                "type": "folder",
                "mimeType": "application/vnd.google-apps.folder",
                "has_children": True,
            }
        ]
        children.extend(_node(item) for item in files if isinstance(item, dict))
        return {"children": children, "next_page_token": data.get("nextPageToken") if isinstance(data, dict) else None}

    if parent_id.startswith("drive:drive/") and parent_id.endswith(":root"):
        drive_id = parent_id.split("/", 1)[1].split(":", 1)[0]
        data = _files_list("'root' in parents and trashed=false", corpora="drive", drive_id=drive_id)
        files = data.get("files", []) if isinstance(data, dict) else []
        return {"children": [_node(item) for item in files if isinstance(item, dict)], "next_page_token": data.get("nextPageToken") if isinstance(data, dict) else None}

    if parent_id.startswith("drive:"):
        file_id = parent_id.split(":", 1)[1]
        query = f"'{file_id}' in parents and trashed=false"
        data = _files_list(query)
        files = data.get("files", []) if isinstance(data, dict) else []
        return {"children": [_node(item) for item in files if isinstance(item, dict)], "next_page_token": data.get("nextPageToken") if isinstance(data, dict) else None}

    return {"children": [], "next_page_token": None}


# ---- Source: Local (read-only listing)

def _local_children(params: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _settings()
    roots: List[str] = [os.path.abspath(path) for path in cfg.get("local_roots", []) if isinstance(path, str)]
    parent_id = params.get("parent_id", "local:root")

    def _mk_node(path: str) -> Dict[str, Any]:
        name = os.path.basename(path) or path
        try:
            is_dir = os.path.isdir(path)
            size = None if is_dir else os.path.getsize(path)
        except Exception:
            is_dir, size = False, None
        return {
            "id": f"local:{_b64u(path)}",
            "name": name,
            "type": "folder" if is_dir else "file",
            "mimeType": None,
            "has_children": bool(is_dir),
            "size": size,
        }

    if parent_id == "local:root":
        return {"children": [_mk_node(root) for root in roots], "next_page_token": None}

    if parent_id.startswith("local:"):
        encoded = parent_id.split(":", 1)[1]
        try:
            path = os.path.abspath(_ub64u(encoded))
        except Exception:
            return {"children": [], "next_page_token": None}
        allowed = False
        for root in roots:
            try:
                if os.path.commonpath([path, root]) == root:
                    allowed = True
                    break
            except ValueError:
                continue
        if not allowed:
            return {"children": [], "next_page_token": None}
        try:
            entries: List[Dict[str, Any]] = []
            with os.scandir(path) as handle:
                for entry in handle:
                    if entry.is_symlink():
                        continue
                    full_path = os.path.join(path, entry.name)
                    entries.append(_mk_node(full_path))
            entries.sort(key=lambda item: (item.get("type") != "folder", item.get("name", "").lower()))
            return {"children": entries, "next_page_token": None}
        except Exception:
            return {"children": [], "next_page_token": None}

    return {"children": [], "next_page_token": None}


# ---- Public PluginV2 surface

def describe() -> Dict[str, Any]:
    return {
        "id": SERVICE_ID,
        "version": VERSION,
        "summary": "Unified reader for Drive/Local (read-only)",
        "capabilities": ["catalog.list", "catalog.search"],
        "requires": ["oauth_refresh_token (drive) or local_roots (local)"],
    }


def register_broker(broker) -> None:
    global _broker, _log
    _broker = broker
    _log = broker.logger(SERVICE_ID)
    try:
        if _log:
            _log.info("registered", service=SERVICE_ID, version=VERSION)
    except Exception:
        pass


def probe(timeout_s: float = 0.9) -> Dict[str, Any]:
    start = time.perf_counter()
    cfg = _settings()
    enabled = cfg.get("enabled", {})
    ok_sources: List[str] = []
    if enabled.get("drive") and _broker is not None:
        cid, cs, rt = _google_client()
        if cid and cs and rt:
            ok_sources.append("drive")
    if enabled.get("local"):
        if cfg.get("local_roots"):
            ok_sources.append("local")
    elapsed = int((time.perf_counter() - start) * 1000)
    status = "ok" if ok_sources else "unconfigured"
    return {
        "ok": bool(ok_sources),
        "status": status,
        "latency_ms": elapsed,
        "details": ",".join(ok_sources) or "no sources configured",
    }


def views() -> List[Dict[str, Any]]:
    return [
        {"id": "reader", "title": "Reader", "ui": "tree", "op": "children"},
    ]


def read(op: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
    op = op or "children"
    params = params or {}
    cfg = _settings()
    enabled = cfg.get("enabled", {})
    source = params.get("source", "drive")
    if op == "children":
        if source == "drive" and enabled.get("drive"):
            return _drive_children(params)
        if source == "local" and enabled.get("local"):
            return _local_children(params)
        return {"children": [], "next_page_token": None}
    if op == "search":
        if source == "drive" and enabled.get("drive") and _broker is not None:
            token = _google_access_token()
            if not token:
                return {"items": []}
            query = params.get("q", "").strip()
            if not query:
                return {"items": []}
            session = _broker.http_session("reader.drive")
            session.headers.update({"Authorization": f"Bearer {token}"})
            limit = int(params.get("limit", 25))
            url = (
                "https://www.googleapis.com/drive/v3/files"
                "?q="
                + urllib.parse.quote(f"name contains '{query}' and trashed=false")
                + f"&pageSize={limit}"
                + "&fields=files(id,name,mimeType,modifiedTime,size)&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=allDrives"
            )
            response = session.get(url, timeout=8)
            if response.status_code != 200:
                return {"items": []}
            payload = response.json()
            if not isinstance(payload, dict):
                return {"items": []}
            files = payload.get("files", [])
            return {"items": files if isinstance(files, list) else []}
        return {"items": []}
    return {"error": "unknown_op"}
