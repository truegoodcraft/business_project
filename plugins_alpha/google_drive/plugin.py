from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from core.contracts.plugin_v2 import PluginV2
from core.conn_broker import ConnectionBroker, ClientHandle


class Plugin(PluginV2):
    id = "google_drive"
    name = "Google Drive Provider"
    version = "0.1"

    def describe(self) -> Dict[str, Any]:
        return {"services": ["drive"], "scopes": ["read_base", "read_crawl"]}

    def register_broker(self, broker: ConnectionBroker) -> None:
        def provider(scope: str) -> Optional[ClientHandle]:
            creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if creds_path and not Path(creds_path).is_absolute():
                creds_path = str((Path(__file__).resolve().parents[2] / creds_path).resolve())
            if not creds_path or not Path(creds_path).exists():
                return None
            scopes = ["https://www.googleapis.com/auth/drive.readonly"]
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            service = build("drive", "v3", credentials=creds, cache_discovery=False)
            return ClientHandle(service="drive", scope=scope, handle=service, metadata={})

        def probe(handle: Optional[ClientHandle]) -> Dict[str, Any]:
            if handle is None:
                cp = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
                if cp and not Path(cp).is_absolute():
                    cp = str((Path(__file__).resolve().parents[2] / cp).resolve())
                if not cp:
                    return {"ok": False, "detail": "missing_credentials", "hint": "Set GOOGLE_APPLICATION_CREDENTIALS or edit .env"}
                if not Path(cp).exists():
                    return {"ok": False, "detail": "creds_path_missing", "hint": f"File not found: {cp}"}
                return {"ok": False, "detail": "client_unavailable"}
            try:
                svc = handle.handle
                svc.files().list(pageSize=1, q="trashed=false", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "detail": "probe_error", "error": str(e)}

        broker.register("drive", provider=provider, probe=probe)
