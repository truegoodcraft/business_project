from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import List

from core.contracts.plugin_v2 import PluginV2


def discover_alpha_plugins() -> List[PluginV2]:
    plugins: List[PluginV2] = []
    search_paths = []
    for base in ("plugins_alpha", "plugins"):
        if Path(base).exists():
            search_paths.append((base, str(Path(base))))
    if not search_paths:
        return plugins

    for base, location in search_paths:
        for _, name, _ in pkgutil.iter_modules([location]):
            module_name = name
            if base == "plugins":
                module_name = f"plugins.{name}"
            elif not name.startswith("plugins_alpha"):
                module_name = f"plugins_alpha.{name}"
            try:
                mod = importlib.import_module(module_name)
                cls = getattr(mod, "Plugin", None)
                if isinstance(cls, type) and issubclass(cls, PluginV2):
                    plugins.append(cls())
            except Exception:
                continue
    return plugins


__all__ = ["discover_alpha_plugins"]
