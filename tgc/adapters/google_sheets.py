"""Google Sheets adapter providing lightweight read access utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .base import AdapterCapability, BaseAdapter
from . import sheets_adapter
from ..config import GoogleSheetsConfig
from ..integration_support import format_sheets_missing_env_message, sheets_share_hint
from ..modules.google_drive import DriveModuleConfig


class GoogleSheetsAdapter(BaseAdapter):
    name = "sheets"
    implementation_state = "implemented"

    def __init__(
        self,
        config: GoogleSheetsConfig,
        drive_config: Optional[DriveModuleConfig] = None,
        *,
        service_account_email: Optional[str] = None,
    ) -> None:
        super().__init__(config)
        self._drive_config = drive_config or DriveModuleConfig()
        self._service_account_email = service_account_email
        self._cached_metadata: Optional[Dict[str, Any]] = None

    def is_configured(self) -> bool:
        return bool(self.config.is_configured() and self._drive_config.has_credentials())

    def capabilities(self) -> List[AdapterCapability]:
        configured = self.is_configured()
        return [
            AdapterCapability(
                name="Inventory preview",
                description="Read configured spreadsheet metadata and sample rows",
                configured=configured,
            ),
            AdapterCapability(
                name="Metrics sync",
                description="Push summarized metrics to dashboard sheet",
                configured=configured,
            )
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        sheet_id = self.config.inventory_sheet_id
        return {
            "inventory_sheet_id": sheet_id,
            "timeout_seconds": str(self._drive_config.timeout_seconds),
            "has_credentials": str(self._drive_config.has_credentials()).lower(),
        }

    def sync_metrics(self, metrics: Dict[str, str]) -> List[str]:
        if not self.is_configured():
            return [self.missing_configuration_message()]
        return [f"Updated {key} -> {value}" for key, value in metrics.items()]

    def missing_configuration_message(self) -> str:
        return format_sheets_missing_env_message(self._service_account_email)

    def implementation_notes(self) -> str:
        return (
            "Adapter provides read-only helpers for Google Sheets while retaining a simulated "
            "metrics sync placeholder."
        )

    def service_account_email(self) -> Optional[str]:
        return self._service_account_email

    # ------------------------------------------------------------------
    # Read helpers used by menu + health checks

    def inventory_metadata(self, *, force_refresh: bool = False) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError(self.missing_configuration_message())
        if not force_refresh and self._cached_metadata is not None:
            return dict(self._cached_metadata)
        sheet_id = self.config.inventory_sheet_id
        if not sheet_id:
            raise RuntimeError("SHEET_INVENTORY_ID is not configured.")
        metadata = sheets_adapter.get_spreadsheet_metadata(
            sheet_id,
            credentials=self._credentials_info(),
            timeout=self._drive_config.timeout_seconds,
        )
        self._cached_metadata = dict(metadata)
        return metadata

    def read_inventory_range(
        self,
        range_a1: str,
        limits: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError(self.missing_configuration_message())
        sheet_id = self.config.inventory_sheet_id
        if not sheet_id:
            raise RuntimeError("SHEET_INVENTORY_ID is not configured.")
        return sheets_adapter.read_range(
            sheet_id,
            range_a1,
            limits,
            credentials=self._credentials_info(),
            timeout=self._drive_config.timeout_seconds,
        )

    def read_inventory_preview(
        self,
        *,
        max_rows: int = 10,
        limits: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        if max_rows <= 0:
            max_rows = 10
        range_a1 = f"A1:Z{max_rows}"
        effective_limits: Dict[str, object] = {"max_rows": max_rows}
        if limits:
            effective_limits.update({key: value for key, value in limits.items() if value is not None})
        return self.read_inventory_range(range_a1, effective_limits)

    def status_report(self) -> Dict[str, object]:
        report = super().status_report()
        if not self.config.inventory_sheet_id:
            return report
        if not self.is_configured():
            report["inventory_access"] = {
                "status": "missing",
                "detail": self.missing_configuration_message(),
            }
            return report
        try:
            metadata = self.inventory_metadata()
        except Exception as exc:  # pragma: no cover - network dependent
            hint = sheets_share_hint(self._service_account_email)
            report["inventory_access"] = {
                "status": "error",
                "detail": f"{exc}. {hint}",
            }
            return report
        sheets = metadata.get("sheets") or []
        sheet_names = [
            entry.get("title")
            for entry in sheets
            if isinstance(entry, Mapping) and entry.get("title")
        ]
        report["inventory_access"] = {
            "status": "ready",
            "detail": f"Spreadsheet {metadata.get('title') or '(untitled)'} ({metadata.get('spreadsheetId')})",
            "sheets": sheet_names,
        }
        return report

    # ------------------------------------------------------------------
    # Internal helpers

    def _credentials_info(self) -> Mapping[str, Any]:
        credentials = self._drive_config.credentials
        if not credentials:
            raise RuntimeError("Drive module credentials are missing; re-run Drive configuration.")
        return credentials
