"""Connection broker issuing scoped service clients for plugins."""

from __future__ import annotations

import logging
import time
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
        handle = supplier(scope)
        if handle is None:
            return None
        self._log_issuance(handle, ok=True)
        return handle

    def probe(self, service: str) -> Dict[str, Any]:
        """Perform a lightweight connectivity probe for ``service``."""

        handle = self.get_client(service, scope="read_base")
        if handle is None:
            return {"service": service, "ok": False, "detail": "client_unavailable"}
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
        service = handle.handle
        metadata = dict(handle.metadata)
        roots = metadata.get("roots") or []
        target = roots[0] if roots else "root"
        try:
            request = service.files().list(  # type: ignore[call-arg]
                pageSize=1,
                q=f"'{target}' in parents and trashed = false" if target and target != "root" else None,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields="files(id)",
            )
            response = request.execute()
            count = len(response.get("files", [])) if isinstance(response, dict) else 0
        except Exception as exc:  # pragma: no cover - network guard
            return {"service": "drive", "ok": False, "detail": str(exc)}
        return {"service": "drive", "ok": True, "metadata": {"root": target, "count": count}}

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
