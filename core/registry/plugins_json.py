"""Simple plugin registry backed by config/plugins.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.unilog import write as uni_write

_CONFIG_PATH = Path("config") / "plugins.json"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        content = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        uni_write("plugin.registry.error", None, error=str(exc), path=str(_CONFIG_PATH))
        return {}
    if not isinstance(content, dict):
        return {}
    return content


def enabled(name: str) -> bool:
    """Return True when the plugin is enabled in the registry."""

    config = _load_config()
    value = config.get(name)
    if value is None:
        return True
    return bool(value)
