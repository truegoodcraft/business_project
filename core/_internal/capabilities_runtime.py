# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Runtime capability registry internals."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from core.plugins_state import is_enabled as _plugin_enabled
from core.unilog import write as uni_write

_CAPABILITIES: Dict[str, Dict[str, Any]] = {}
_DECLARED: Dict[str, Dict[str, Any]] = {}


def publish_capability(
    name: str,
    *,
    plugin: str,
    version: str,
    scopes: list[str],
    func: Callable[..., Any],
    network: bool = False,
) -> None:
    _CAPABILITIES[name] = {
        "plugin": plugin,
        "version": version,
        "scopes": list(scopes),
        "func": func,
        "network": bool(network),
    }


def declare_capabilities(plugin: str, version: str, capabilities: list[dict[str, Any]]) -> None:
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


def unpublish_capability(name: str) -> None:
    _CAPABILITIES.pop(name, None)


def resolve_capability(name: str) -> Callable[..., Any]:
    return capability_meta(name)["func"]


def capability_meta(name: str) -> Dict[str, Any]:
    try:
        return _CAPABILITIES[name]
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


def list_published_capabilities() -> Dict[str, Dict[str, Any]]:
    return {name: dict(meta) for name, meta in _CAPABILITIES.items()}


def reset_runtime_capabilities() -> None:
    _CAPABILITIES.clear()
    _DECLARED.clear()
