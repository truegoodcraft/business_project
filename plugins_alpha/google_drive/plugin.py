from __future__ import annotations

from core.conn_broker import ConnectionBroker
from core.contracts.plugin_v2 import PluginV2


class Plugin(PluginV2):
    id = "google_drive"
    name = "Google Drive Provider (disabled)"
    version = "0.0"
    api_version = "2"

    def describe(self):
        return {"services": [], "scopes": []}

    def register_broker(self, broker: ConnectionBroker):
        return None
