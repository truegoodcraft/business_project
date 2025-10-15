from __future__ import annotations

from core.conn_broker import ConnectionBroker, ClientHandle
from core.contracts.plugin_v2 import PluginV2


class Plugin(PluginV2):
    id = "google_drive"
    name = "Google Drive Provider (disabled)"
    version = "0.0"
    api_version = "2"

    def describe(self):
        import os, pathlib

        creds = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "") or "").strip()
        root_ids = (os.environ.get("DRIVE_ROOT_IDS", "") or "").strip()
        if not creds or not root_ids or not pathlib.Path(os.path.expanduser(creds)).exists():
            return {"services": [], "scopes": []}  # hidden until ready
        return {"services": ["drive"], "scopes": ["read_base"]}

    def register_broker(self, broker: ConnectionBroker):
        import os, pathlib

        creds = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "") or "").strip()
        root_ids = (os.environ.get("DRIVE_ROOT_IDS", "") or "").strip()
        if not creds or not root_ids or not pathlib.Path(os.path.expanduser(creds)).exists():
            return  # do not register; prevents /probe from touching it

        def provider(scope: str):
            return ClientHandle(service="drive", scope=scope, handle={"configured": True})

        def probe(handle):
            return {"ok": True, "detail": "drive_config_present"}

        broker.register("drive", provider=provider, probe=probe)

    def capabilities(self):
        return {
            "provides": ["drive.files.read"],
            "requires": ["auth.google.service_account"],
            "trust_tier": 1,
            "stages": ["service"],
        }
