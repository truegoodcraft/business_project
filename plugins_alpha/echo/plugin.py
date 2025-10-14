from core.contracts.plugin_v2 import PluginV2
from core.conn_broker import ConnectionBroker, ClientHandle


class Plugin(PluginV2):
    id = "echo"
    name = "Echo Service"
    version = "0.1"
    api_version = "2"

    def describe(self):
        return {"services": ["echo"], "scopes": ["read_base"]}

    def register_broker(self, broker: ConnectionBroker):
        def provider(scope: str):
            return ClientHandle(service="echo", scope=scope, handle={"scope": scope})

        def probe(handle):
            return {"ok": True, "detail": "echo_ready"}

        broker.register("echo", provider=provider, probe=probe)
