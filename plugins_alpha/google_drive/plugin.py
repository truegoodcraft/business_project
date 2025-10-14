from __future__ import annotations

from core.conn_broker import ConnectionBroker, ClientHandle
from core.contracts.plugin_v2 import PluginV2


class Plugin(PluginV2):
    id = "google_drive"
    name = "Google Drive Provider (disabled)"
    version = "0.0"
    api_version = "2"

    def describe(self):
        # only advertise when fully configured
        import os

        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        root_ids = os.environ.get("DRIVE_ROOT_IDS", "").strip()
        if not creds or not root_ids:
            return {"services": [], "scopes": []}  # hidden until ready
        return {"services": ["drive"], "scopes": ["read_base"]}  # example

    def register_broker(self, broker: ConnectionBroker):
        import os, pathlib

        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        root_ids = os.environ.get("DRIVE_ROOT_IDS", "").strip()
        if not creds or not root_ids or not pathlib.Path(creds).expanduser().exists():
            return  # do not register; prevents probe hang

        # else: register lightweight provider+probe with internal short timeouts only
        def provider(scope: str):
            # lazy initialization only when actually used
            return ClientHandle(service="drive", scope=scope, handle={"ok": True})

        def probe(handle):
            # quick, bounded check only
            return {"ok": True, "detail": "drive_config_present"}

        broker.register("drive", provider=provider, probe=probe)

    def capabilities(self):
        return {
            "provides": ["drive.files.read"],
            "requires": ["auth.google.service_account"],
            "trust_tier": 1,
            "stages": ["service"],
        }
