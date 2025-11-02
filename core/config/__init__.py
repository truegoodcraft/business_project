"""Configuration package exposing path helpers and legacy accessors."""

from . import paths as paths
from .paths import (
    APP_DIR,
    BUS_ROOT,
    DATA_DIR,
    DB_PATH,
    DB_URL,
    DEFAULT_UI_DIR,
    DEV_UI_DIR,
    IMPORTS_DIR,
    JOURNALS_DIR,
    UI_DIR,
)

__all__ = [
    "paths",
    "APP_DIR",
    "BUS_ROOT",
    "DATA_DIR",
    "DB_PATH",
    "DB_URL",
    "DEFAULT_UI_DIR",
    "DEV_UI_DIR",
    "IMPORTS_DIR",
    "JOURNALS_DIR",
    "UI_DIR",
]

try:  # pragma: no cover - fallback for legacy config helpers
    from core import config_legacy as _legacy
except ImportError:  # pragma: no cover
    _legacy = None
else:
    load_core_config = _legacy.load_core_config
    load_plugin_config = _legacy.load_plugin_config
    plugin_env_whitelist = _legacy.plugin_env_whitelist

    __all__.extend(
        [
            "load_core_config",
            "load_plugin_config",
            "plugin_env_whitelist",
        ]
    )

