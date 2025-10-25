from __future__ import annotations
from typing import Dict, Any, Optional
from core.services.conn_broker import ConnectionBroker


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

    def plan_transform(self, fn: str, payload: Dict[str, Any], *, limits: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError("transform planning not implemented")

    def manifest(self) -> Dict[str, Any]:
        block = self.capabilities() or {}
        return {
            "id": getattr(self, "id", self.__class__.__name__),
            "version": getattr(self, "version", "0"),
            "provides": list(block.get("provides", [])),
            "requires": list(block.get("requires", [])),
            "stages": list(block.get("stages", [])),
            "trust_tier": block.get("trust_tier", 1),
        }
