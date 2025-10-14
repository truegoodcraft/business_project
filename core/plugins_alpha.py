from __future__ import annotations
import importlib
import pkgutil
from typing import List
from core.contracts.plugin_v2 import PluginV2


def discover_alpha_plugins() -> List[PluginV2]:
    plugins: List[PluginV2] = []
    for _, name, _ in pkgutil.iter_modules(['plugins_alpha']):
        try:
            mod = importlib.import_module(f"plugins_alpha.{name}")
        except Exception:
            continue
        cls = getattr(mod, "Plugin", None)
        if cls and issubclass(cls, PluginV2):
            plugins.append(cls())
    return plugins
