"""Google Sheets adapter placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import GoogleSheetsConfig
from ..integration_support import format_sheets_missing_env_message


class GoogleSheetsAdapter(BaseAdapter):
    name = "sheets"

    def __init__(
        self, config: GoogleSheetsConfig, *, service_account_email: Optional[str] = None
    ) -> None:
        super().__init__(config)
        self._service_account_email = service_account_email

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability(
                name="Metrics sync",
                description="Push summarized metrics to dashboard sheet",
                configured=self.is_configured(),
            )
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {"inventory_sheet_id": self.config.inventory_sheet_id}

    def sync_metrics(self, metrics: Dict[str, str]) -> List[str]:
        if not self.is_configured():
            return [self.missing_configuration_message()]
        return [f"Updated {key} -> {value}" for key, value in metrics.items()]

    def missing_configuration_message(self) -> str:
        return format_sheets_missing_env_message(self._service_account_email)

    def implementation_notes(self) -> str:
        return (
            "Placeholder Google Sheets adapter; write operations are simulated pending API wiring."
        )
