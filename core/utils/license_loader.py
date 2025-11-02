"""Local license loader and helpers for feature gating."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_TIER = "community"
DEFAULT_FEATURES: Dict[str, bool] = {
    "rfq": False,
    "batch_run": False,
    "import_commit": False,
}


def _baseline_license() -> Dict[str, Any]:
    return {
        "tier": DEFAULT_TIER,
        "features": dict(DEFAULT_FEATURES),
        "plugins": {},
    }


def _license_path() -> Path:
    """Return the expected license path respecting ``BUS_ROOT`` when set."""

    bus_root = os.environ.get("BUS_ROOT")
    if bus_root:
        return Path(bus_root).resolve() / "license.json"

    local_root = os.environ.get("LOCALAPPDATA")
    if not local_root:
        local_root = str(Path.home() / "AppData" / "Local")
    return (Path(local_root) / "BUSCore" / "license.json").resolve()


def _normalize_license(raw: Any) -> Dict[str, Any]:
    data = _baseline_license()
    if not isinstance(raw, dict):
        return data

    tier = raw.get("tier")
    if isinstance(tier, str) and tier.strip():
        data["tier"] = tier

    raw_features = raw.get("features")
    if isinstance(raw_features, dict):
        for key, value in raw_features.items():
            if isinstance(value, bool):
                data["features"][str(key)] = value
            elif isinstance(value, dict):
                flag = value.get("enabled")
                if isinstance(flag, bool):
                    data["features"][str(key)] = flag
                else:
                    data["features"][str(key)] = bool(flag)
            else:
                data["features"][str(key)] = bool(value)

    raw_plugins = raw.get("plugins")
    if isinstance(raw_plugins, dict):
        normalized_plugins: Dict[str, Any] = {}
        for key, value in raw_plugins.items():
            normalized_plugins[str(key)] = value
        data["plugins"] = normalized_plugins

    return data


def get_license(*, force_reload: bool | None = None) -> Dict[str, Any]:
    """Read license from disk. When BUS_ROOT is set, always reload from disk."""

    if force_reload is None:
        force_reload = bool(os.environ.get("BUS_ROOT"))

    path = _license_path()
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    except Exception:
        raw = {}

    data = _normalize_license(raw)
    data.setdefault("tier", DEFAULT_TIER)
    data.setdefault("features", {})
    data.setdefault("plugins", {})
    return data


def feature_enabled(name: str) -> bool:
    lic = get_license()
    features = lic.get("features")
    if isinstance(features, dict):
        value = features.get(name)
        if isinstance(value, bool):
            return value
        if isinstance(value, dict):
            flag = value.get("enabled")
            if isinstance(flag, bool):
                return flag
            return bool(flag)
        if value is not None:
            return bool(value)
    return bool(DEFAULT_FEATURES.get(name, False))


def plugin_enabled(pid: str) -> bool:
    lic = get_license()
    plugins = lic.get("plugins")
    if isinstance(plugins, dict):
        entry = plugins.get(pid)
        if isinstance(entry, bool):
            return entry
        if isinstance(entry, dict):
            flag = entry.get("enabled")
            if isinstance(flag, bool):
                return flag
            return bool(flag)
        if entry is not None:
            return bool(entry)
    return True


def license_path() -> Path:
    """Return the path to the license file."""

    return _license_path()


__all__ = [
    "DEFAULT_FEATURES",
    "DEFAULT_TIER",
    "feature_enabled",
    "get_license",
    "license_path",
    "plugin_enabled",
]
