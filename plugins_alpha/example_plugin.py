from __future__ import annotations

from typing import Dict

from core.contracts.plugin_v2 import PluginV2


class Plugin(PluginV2):
    """Minimal example plugin used for alpha bootstrapping."""

    id = "example"
    name = "Example Alpha Plugin"

    def describe(self) -> Dict[str, object]:
        base = super().describe()
        services = set(base.get("services", []))
        services.add("drive")
        base["services"] = sorted(services)
        return base

    def probe(self, broker) -> Dict[str, object]:
        return broker.probe("drive")
