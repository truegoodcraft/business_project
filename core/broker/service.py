from __future__ import annotations
from typing import Any, Dict
from .jsonrpc import unpack_frame, pack, res, err
from .pipes import PipeConnection

class PluginBroker:
    """
    Thin dispatcher for plugin requests. No secrets; read-only services later.
    """
    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "hello":   # params: {plugin_id, api_version}
            return {"ok": True}
        if method == "ping":
            return {"ok": True}
        raise KeyError("Method not found")

def handle_connection(conn: PipeConnection, broker: PluginBroker):
    while True:
        try:
            req_obj = unpack_frame(conn.read_frame())
        except Exception:
            break
        mid = req_obj.get("id", 0)
        try:
            result = broker.dispatch(req_obj.get("method",""), req_obj.get("params",{}))
            conn.write_frame(pack(res(mid, result)))
        except Exception as e:
            conn.write_frame(pack(err(mid, -32601, str(e))))
