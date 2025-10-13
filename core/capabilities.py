"""Capability registry with plugin metadata."""

from __future__ import annotations

import os
from typing import Dict

from core.plugins_state import is_enabled as _plugin_enabled
from core.unilog import write as uni_write

REGISTRY: dict[str, dict] = {}  # name -> {plugin, version, scopes, func, network}
_DECLARED: Dict[str, dict] = {}


def register(name: str, plugin: str, version: str, scopes: list[str], func, network: bool = False):
    REGISTRY[name] = {
        "plugin": plugin,
        "version": version,
        "scopes": scopes,
        "func": func,
        "network": bool(network),
    }


def declare(plugin: str, version: str, capabilities: list[dict]):
    """Record capability metadata even if the plugin is disabled."""

    for cap in capabilities:
        name = cap.get("name")
        if not isinstance(name, str):
            continue
        _DECLARED[name] = {
            "plugin": plugin,
            "version": version,
            "network": bool(cap.get("network", False)),
        }


def resolve(name: str):
    return meta(name)["func"]


def meta(name: str):
    try:
        return REGISTRY[name]
    except KeyError:
        info = _DECLARED.get(name)
        if info is None:
            raise KeyError(f"Capability '{name}' is not registered.") from None
        plugin = info["plugin"]
        if not _plugin_enabled(plugin):
            print("Plugin disabled. Open Plugins Hub → Enable/Disable.")
            uni_write(
                "capability.resolve.fail",
                None,
                capability=name,
                plugin=plugin,
                reason="plugin_disabled",
            )
        else:
            from core.config import plugin_env_whitelist

            missing_env = [key for key in plugin_env_whitelist(plugin) if not os.getenv(key)]
            if missing_env:
                print("Plugin missing configuration. Configure via Plugins Hub → Configure.")
                uni_write(
                    "capability.resolve.fail",
                    None,
                    capability=name,
                    plugin=plugin,
                    reason="missing_env",
                    missing_env=missing_env,
                )
            else:
                print("Capability unavailable. Re-run Plugins Hub → Discover for details.")
                uni_write(
                    "capability.resolve.fail",
                    None,
                    capability=name,
                    plugin=plugin,
                    reason="not_loaded",
                )
        raise KeyError(f"Capability '{name}' is not available.") from None
