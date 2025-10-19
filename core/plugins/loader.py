"""Lightweight plugin module registry."""

from __future__ import annotations

from types import ModuleType
from typing import Dict

_PLUGINS: Dict[str, ModuleType] = {}


def register(module: ModuleType) -> None:
    service_id = getattr(module, "SERVICE_ID", None)
    if not service_id:
        return
    _PLUGINS[str(service_id)] = module


def get_plugin(service_id: str):
    return _PLUGINS.get(service_id)


def all_plugins() -> Dict[str, ModuleType]:
    return dict(_PLUGINS)
