from core.contracts.plugin_v2 import PluginV2
from core.conn_broker import ConnectionBroker, ClientHandle


class Plugin(PluginV2):
    id = "echo"
    name = "Echo Service"
    version = "0.1"
    api_version = "2"

    def describe(self):
        return {"services": ["echo"], "scopes": ["read_base"]}

    def capabilities(self):
        return {"provides": ["echo.service"], "requires": [], "trust_tier": 1, "stages": ["service"]}

    def register_broker(self, broker: ConnectionBroker):
        def provider(scope: str):
            return ClientHandle(service="echo", scope=scope, handle={"scope": scope})

        def probe(handle):
            return {"ok": True, "detail": "echo_ready"}  # returns immediately

        broker.register("echo", provider=provider, probe=probe)

    def plan_transform(self, fn: str, payload, *, limits=None):
        if fn != "noop":
            raise ValueError("unknown_transform")
        summary = {"echo": payload}
        return {"operations": [], "summary": summary}
