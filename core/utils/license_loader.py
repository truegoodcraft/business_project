"""Local license loader and helpers for feature gating."""

from __future__ import annotations

import json
import os
from copy import deepcopy
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
    bus_root = os.environ.get("BUS_ROOT")
    if bus_root:
        root = Path(bus_root).expanduser()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            root = Path(local_app_data).expanduser() / "BUSCore"
        else:
            root = Path.home() / "AppData" / "Local" / "BUSCore"
    return root / "license.json"


def _write_license(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


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


def _load_license() -> Dict[str, Any]:
    path = _license_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = _baseline_license()
        _write_license(path, data)
        return data
    except json.JSONDecodeError:
        data = _baseline_license()
        _write_license(path, data)
        return data
    except Exception:
        return _baseline_license()

    return _normalize_license(raw)


_LICENSE_DATA: Dict[str, Any] = _load_license()
_LICENSE_PATH: Path = _license_path()


def reload_license() -> Dict[str, Any]:
    """Reload the license from disk and update cached state."""

    global _LICENSE_DATA, _LICENSE_PATH
    _LICENSE_DATA = _load_license()
    _LICENSE_PATH = _license_path()
    return get_license()


def get_license() -> Dict[str, Any]:
    """Return a copy of the currently loaded license."""

    return deepcopy(_LICENSE_DATA)


def license_path() -> Path:
    """Return the path to the license file."""

    return _LICENSE_PATH


def feature_enabled(name: str) -> bool:
    """Return whether the named feature is enabled."""

    features = _LICENSE_DATA.get("features")
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
    """Return whether the plugin with ``pid`` is enabled."""

    plugins = _LICENSE_DATA.get("plugins")
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


__all__ = [
    "DEFAULT_FEATURES",
    "DEFAULT_TIER",
    "feature_enabled",
    "get_license",
    "license_path",
    "plugin_enabled",
    "reload_license",
]
