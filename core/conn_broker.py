"""Connection broker issuing scoped service clients for plugins."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ClientHandle:
    """Lightweight wrapper describing an issued client handle."""

    service: str
    scope: str
    handle: Any
    issued_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionBroker:
    """Mediate access to integration clients with scoped issuance."""

    def __init__(self, controller: Any, *, logger: Optional[logging.Logger] = None) -> None:
        self._controller = controller
        self._logger = logger or logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API

    def get_client(self, service: str, scope: str = "read_base") -> Optional[ClientHandle]:
        """Return a scoped client handle for ``service`` if available."""

        service = service.lower()
        scope = scope.lower()
        supplier = getattr(self, f"_issue_{service}_client", None)
        if supplier is None:
            self._logger.warning("broker.issue.unsupported", extra={"service": service, "scope": scope})
            return None
        if not hasattr(self, "_grants"):
            self._grants: Dict[str, str] = {}
        if not hasattr(self, "_escalation_logged"):
            self._escalation_logged: set[str] = set()
        _order = {"read_base": 0, "read_crawl": 1, "write": 2}
        prev = self._grants.get(service)
        escalation = prev is not None and _order.get(scope, 0) > _order.get(prev, 0)
        if escalation and scope == "write":
            if service not in self._escalation_logged:
                self._logger.warning(
                    "broker.escalation.denied",
                    extra={"service": service, "from": prev, "to": scope},
                )
                self._escalation_logged.add(service)
            return None
        handle = supplier(scope)
        if handle is None:
            return None
        if prev is None or _order.get(scope, 0) >= _order.get(prev, 0):
            self._grants[service] = scope
        self._log_issuance(handle, ok=True)
        return handle

    def probe(self, service: str) -> Dict[str, Any]:
        """Perform a lightweight connectivity probe for ``service``."""

        handle = self.get_client(service, scope="read_base")
        if handle is None:
            detail = "client_unavailable"
            hint: Optional[str] = None
            service_lower = service.lower()
            if service_lower == "drive":
                creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
                if not creds:
                    detail = "missing_credentials"
                    hint = "Set GOOGLE_APPLICATION_CREDENTIALS or edit .env"
                elif not Path(creds).exists():
                    detail = "creds_path_missing"
                    hint = f"File not found: {creds}"
            elif service_lower == "sheets":
                adapter = self._controller_adapter("sheets")
                if adapter is None:
                    detail = "adapter_missing"
                    hint = "Sheets adapter not available"
                elif not getattr(adapter, "is_configured", lambda: False)():
                    detail = "not_configured"
                    inventory_id = getattr(getattr(adapter, "config", None), "inventory_sheet_id", None)
                    hint = "Set SHEET_INVENTORY_ID in .env" if not inventory_id else None
            elif service_lower == "notion":
                module = self._controller_module("notion_access")
                if module is None:
                    detail = "module_missing"
                    hint = "Notion module not available"
                else:
                    token = getattr(module, "_token", None)
                    if not token:
                        detail = "missing_credentials"
                        hint = "Set NOTION_TOKEN in .env"
            result = {"service": service, "ok": False, "detail": detail}
            if hint:
                result["hint"] = hint
            return result
        probe_fn = getattr(self, f"_probe_{handle.service}", None)
        if probe_fn is None:
            return {"service": service, "ok": True, "metadata": handle.metadata}
        try:
            return probe_fn(handle)
        except Exception as exc:  # pragma: no cover - defensive network guard
            self._logger.warning(
                "broker.probe.failed",
                extra={"service": handle.service, "scope": handle.scope, "error": str(exc)[:200]},
            )
            return {"service": service, "ok": False, "detail": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers

    def _log_issuance(self, handle: ClientHandle, *, ok: bool) -> None:
        masked: Dict[str, Any] = {"scope": handle.scope, "service": handle.service, "issued_at": handle.issued_at}
        if handle.metadata:
            masked["meta"] = {key: self._mask_value(value) for key, value in handle.metadata.items()}
        level = logging.INFO if ok else logging.WARNING
        self._logger.log(level, "broker.client.issued", extra=masked)

    def _mask_value(self, value: Any) -> Any:
        if isinstance(value, str):
            if len(value) <= 6:
                return "*" * len(value)
            return f"{value[:3]}***{value[-3:]}"
        if isinstance(value, (list, tuple)):
            return [self._mask_value(item) for item in value]
        return value

    def _controller_module(self, key: str) -> Any:
        modules = getattr(self._controller, "modules", {})
        if isinstance(modules, dict):
            return modules.get(key)
        return None

    def _controller_adapter(self, key: str) -> Any:
        adapters = getattr(self._controller, "adapters", {})
        if isinstance(adapters, dict):
            return adapters.get(key)
        return None

    # ------------------------------------------------------------------
    # Issuers per service

    def _issue_drive_client(self, scope: str) -> Optional[ClientHandle]:
        module = self._controller_module("drive")
        if module is None:
            self._logger.warning("broker.drive.missing_module")
            return None
        creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not creds:
            self._logger.warning("broker.drive.missing_creds_env")
            return None
        if not Path(creds).exists():
            self._logger.warning("broker.drive.creds_path_missing", extra={"path": creds})
            return None
        require_write = scope == "write"
        service, error = module.ensure_service(require_write=require_write)
        if not service:
            self._logger.warning(
                "broker.drive.client_error", extra={"scope": scope, "detail": (error or "unknown")}  # type: ignore[arg-type]
            )
            return None
        metadata = {"roots": list(getattr(module, "root_ids")() or [])}
        return ClientHandle(service="drive", scope=scope, handle=service, metadata=metadata)

    def _issue_notion_client(self, scope: str) -> Optional[ClientHandle]:
        module = self._controller_module("notion_access")
        if module is None:
            self._logger.warning("broker.notion.missing_module")
            return None
        builder = getattr(module, "_build_client", None)
        if builder is None:
            self._logger.warning("broker.notion.builder_missing")
            return None
        client, error = builder()
        if not client:
            self._logger.warning(
                "broker.notion.client_error", extra={"scope": scope, "detail": (error or "unknown")}  # type: ignore[arg-type]
            )
            return None
        metadata = {"roots": list(getattr(module, "_configured_root_ids", lambda: [])())}
        return ClientHandle(service="notion", scope=scope, handle=client, metadata=metadata)

    def _issue_sheets_client(self, scope: str) -> Optional[ClientHandle]:
        adapter = self._controller_adapter("sheets")
        if adapter is None:
            self._logger.warning("broker.sheets.missing_adapter")
            return None
        if not getattr(adapter, "is_configured", lambda: False)():
            self._logger.warning("broker.sheets.not_configured")
            return None
        metadata = {"sheet_id": getattr(adapter.config, "inventory_sheet_id", None)}
        return ClientHandle(service="sheets", scope=scope, handle=adapter, metadata=metadata)

    # ------------------------------------------------------------------
    # Probe helpers

    def _probe_drive(self, handle: ClientHandle) -> Dict[str, Any]:
        try:
            service = handle.handle
            service.files().list(  # type: ignore[call-arg]
                pageSize=1,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields="files(id)",
            ).execute()
            return {"service": "drive", "ok": True}
        except Exception as exc:  # pragma: no cover - network guard
            return {"service": "drive", "ok": False, "detail": "probe_error", "error": str(exc)}

    def _probe_notion(self, handle: ClientHandle) -> Dict[str, Any]:
        client = handle.handle
        metadata = dict(handle.metadata)
        roots = metadata.get("roots") or []
        root_id = roots[0] if roots else None
        try:
            if root_id:
                result = client.databases_retrieve(root_id)  # type: ignore[attr-defined]
                title = result.get("title", []) if isinstance(result, dict) else []
                count = len(title) if isinstance(title, list) else 0
                meta = {"root": root_id, "title_len": count, "pages": count}
            else:
                who = client.users_me()  # type: ignore[attr-defined]
                meta = {"root": None, "user": who.get("name") if isinstance(who, dict) else None}
        except Exception as exc:  # pragma: no cover - network guard
            return {"service": "notion", "ok": False, "detail": str(exc)}
        return {"service": "notion", "ok": True, "metadata": meta}

    def _probe_sheets(self, handle: ClientHandle) -> Dict[str, Any]:
        adapter = handle.handle
        try:
            metadata = adapter.inventory_metadata(force_refresh=True)
            title = metadata.get("title")
        except Exception as exc:  # pragma: no cover - network guard
            return {"service": "sheets", "ok": False, "detail": str(exc)}
        return {
            "service": "sheets",
            "ok": True,
            "metadata": {
                "inventory_id": metadata.get("spreadsheetId"),
                "title": title,
                "sheet_count": len(metadata.get("sheets", [])) if isinstance(metadata.get("sheets"), list) else 0,
            },
        }
