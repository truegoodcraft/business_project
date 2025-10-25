"""Lightweight plugin module registry with discovery helpers."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Dict, Iterable, List, Optional


MODULE_DIR = Path(__file__).resolve().parent
CORE_DIR = MODULE_DIR.parent
ROOT_DIR = CORE_DIR.parent

BUILTIN_PLUGIN_ROOT = os.path.abspath(CORE_DIR / "plugins_builtin")
ALPHA_PLUGIN_ROOT = os.path.abspath(ROOT_DIR / "plugins")
USER_PLUGIN_ROOT = os.path.abspath(ROOT_DIR / "plugins_user")

_PLUGIN_ROOTS: List[tuple[str, str]] = [
    (BUILTIN_PLUGIN_ROOT, "core.plugins_builtin"),
    (ALPHA_PLUGIN_ROOT, "plugins"),
    (USER_PLUGIN_ROOT, "plugins_user"),
]

_PLUGINS: Dict[str, ModuleType] = {}
_PLUGIN_INFO: Dict[str, Dict[str, object]] = {}
_LOADED = False

_SETTINGS_PATH = Path("data/settings_plugins.json")


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    for root, base_module in _PLUGIN_ROOTS:
        if not root or not os.path.isdir(root):
            continue
        root_path = Path(root)
        for plugin_file in sorted(root_path.rglob("plugin.py")):
            if plugin_file.name != "plugin.py":
                continue
            try:
                relative = plugin_file.relative_to(root_path)
            except ValueError:
                continue
            parts = list(relative.parts[:-1])
            if not parts:
                continue
            if any(part.startswith("_") for part in parts):
                continue
            module_name = ".".join([base_module, *parts, "plugin"])
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            register(module)
    _LOADED = True


def _collect_metadata(service_id: str, module: ModuleType) -> Dict[str, object]:
    plugin_path = Path(getattr(module, "__file__", "") or "").resolve()
    plugin_dir = plugin_path.parent if plugin_path.exists() else None
    plugin_dir_str = str(plugin_dir) if plugin_dir else ""
    builtin = False
    if plugin_dir_str:
        try:
            builtin = os.path.commonpath([plugin_dir_str, BUILTIN_PLUGIN_ROOT]) == BUILTIN_PLUGIN_ROOT
        except Exception:
            builtin = False

    describe_data: Dict[str, object] = {}
    describe_fn = getattr(module, "describe", None)
    if callable(describe_fn):
        try:
            data = describe_fn() or {}
            if isinstance(data, dict):
                describe_data = data
        except Exception:
            describe_data = {}

    def _list_from(value: Optional[Iterable[object]]) -> List[str]:
        if not value:
            return []
        return [str(item) for item in value if isinstance(item, str)]

    name = str(
        describe_data.get("name")
        or getattr(module, "NAME", "")
        or service_id
    )
    version = str(
        describe_data.get("version")
        or getattr(module, "VERSION", "")
        or ""
    )

    ui_block: Dict[str, Any] = {}
    if isinstance(describe_data.get("ui"), dict):
        ui_data = describe_data.get("ui") or {}
        tools_pages_raw = ui_data.get("tools_pages") if isinstance(ui_data, dict) else []
        tools_pages: List[Dict[str, Any]] = []
        if isinstance(tools_pages_raw, list):
            for page in tools_pages_raw:
                if not isinstance(page, dict):
                    continue
                pid = str(page.get("id") or "").strip()
                title = str(page.get("title") or "").strip()
                path = str(page.get("path") or "").strip()
                if not pid or not title or not path:
                    continue
                entry: Dict[str, Any] = {"id": pid, "title": title, "path": path}
                if isinstance(page.get("order"), (int, float)):
                    entry["order"] = int(page.get("order"))
                tools_pages.append(entry)
        if tools_pages:
            ui_block["tools_pages"] = tools_pages

    record: Dict[str, Any] = {
        "id": service_id,
        "name": name,
        "version": version,
        "services": _list_from(describe_data.get("services")),
        "scopes": _list_from(describe_data.get("scopes")),
        "capabilities": _list_from(describe_data.get("capabilities")),
        "builtin": builtin,
        "plugin_dir": plugin_dir_str,
    }
    if ui_block:
        record["ui"] = ui_block
    return record


def _load_plugin_settings() -> Dict[str, object]:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_plugin_settings(data: Dict[str, object]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _is_plugin_enabled(pid: str, default: bool = True) -> bool:
    settings = _load_plugin_settings() or {}
    enabled = settings.get("enabled")
    if isinstance(enabled, dict) and pid in enabled:
        return bool(enabled.get(pid))
    return bool(default)


def set_plugin_enabled(pid: str, enabled: bool) -> None:
    settings = _load_plugin_settings() or {}
    enabled_block = settings.get("enabled")
    if not isinstance(enabled_block, dict):
        enabled_block = {}
    enabled_block[pid] = bool(enabled)
    settings["enabled"] = enabled_block
    _save_plugin_settings(settings)


def register(module: ModuleType) -> None:
    service_id = getattr(module, "SERVICE_ID", None)
    if not service_id:
        return
    sid = str(service_id)
    _PLUGINS[sid] = module
    _PLUGIN_INFO[sid] = _collect_metadata(sid, module)


def get_plugin(service_id: str):
    _ensure_loaded()
    return _PLUGINS.get(service_id)


def all_plugins() -> Dict[str, ModuleType]:
    _ensure_loaded()
    return dict(_PLUGINS)


def plugin_descriptor(service_id: str) -> Optional[Dict[str, object]]:
    _ensure_loaded()
    info = _PLUGIN_INFO.get(service_id)
    if not info:
        return None
    record = dict(info)
    builtin = bool(record.get("builtin"))
    record["enabled"] = _is_plugin_enabled(service_id, default=True if builtin else True)
    return record


def iter_descriptors() -> List[Dict[str, object]]:
    _ensure_loaded()
    out: List[Dict[str, object]] = []
    for service_id, info in _PLUGIN_INFO.items():
        record = plugin_descriptor(service_id)
        if record is None:
            continue
        out.append(record)
    return out


__all__ = [
    "BUILTIN_PLUGIN_ROOT",
    "all_plugins",
    "get_plugin",
    "iter_descriptors",
    "plugin_descriptor",
    "register",
    "set_plugin_enabled",
]
