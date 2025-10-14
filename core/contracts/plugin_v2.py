from __future__ import annotations
from typing import Dict, Any, Optional
from core.conn_broker import ConnectionBroker


class PluginV2:
    id: str = "plugin"
    name: str = "Alpha Plugin"
    version: str = "0.1"

    def describe(self) -> Dict[str, Any]:
        return {"services": [], "scopes": ["read_base"]}

    def register_broker(self, broker: ConnectionBroker) -> None:
        """Plugins must call broker.register(service, provider=..., probe=...) for each service."""
        raise NotImplementedError

    def run(self, broker: ConnectionBroker, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": True}
