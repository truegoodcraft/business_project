from __future__ import annotations
from typing import Dict, Any, Optional
from core.conn_broker import ConnectionBroker


class PluginV2:
    id: str = "plugin"
    name: str = "Alpha Plugin"
    version: str = "0.1"
    api_version: str = "2"

    def describe(self) -> Dict[str, Any]:
        return {"services": [], "scopes": ["read_base"]}

    def register_broker(self, broker: ConnectionBroker) -> None:
        raise NotImplementedError

    def run(self, broker: ConnectionBroker, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": True}

    def capabilities(self) -> Dict[str, Any]:
        """Return a declarative capability manifest block."""

        return {
            "provides": [],
            "requires": [],
            "trust_tier": 1,
            "stages": ["service"],
        }
