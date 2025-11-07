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

"""Public capabilities facade."""

from __future__ import annotations

from typing import Any, Callable, Dict

from core.services.capabilities.registry import CapabilityRegistry
from core._internal.capabilities_runtime import (
    capability_meta,
    list_published_capabilities,
    publish_capability,
    resolve_capability,
    unpublish_capability,
)

registry = CapabilityRegistry(plugin_api_version="2")


def publish(
    name: str,
    *,
    plugin: str,
    version: str,
    scopes: list[str],
    func: Callable[..., Any],
    network: bool = False,
) -> None:
    publish_capability(
        name,
        plugin=plugin,
        version=version,
        scopes=scopes,
        func=func,
        network=network,
    )


def unpublish(name: str) -> None:
    unpublish_capability(name)


def list_caps() -> Dict[str, Dict[str, Any]]:
    return list_published_capabilities()


def resolve(name: str):
    return resolve_capability(name)


def meta(name: str) -> Dict[str, Any]:
    return capability_meta(name)


def emit_manifest() -> Dict[str, Any]:
    return registry.emit_manifest()


def emit_manifest_async() -> Dict[str, Any]:
    return registry.emit_manifest_async()


def update_from_probe(service_id: str, capabilities: list[str], probe: Dict[str, Any]) -> None:
    registry.update_from_probe(service_id, capabilities, probe)


def export() -> Dict[str, Dict[str, Any]]:
    return registry.export()
