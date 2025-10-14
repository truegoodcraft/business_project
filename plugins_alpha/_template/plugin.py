from core.contracts.plugin_v2 import PluginV2
from core.conn_broker import ConnectionBroker, ClientHandle


class Plugin(PluginV2):
    id = "your_plugin_id"
    name = "Your Plugin Name"
    version = "0.1"
    api_version = "2"

    def describe(self):
        return {"services": [], "scopes": ["read_base"]}

    def register_broker(self, broker: ConnectionBroker):
        # broker.register("service_name", provider=..., probe=...)
        pass

    def run(self, broker: ConnectionBroker, options=None):
        return {"ok": True}
