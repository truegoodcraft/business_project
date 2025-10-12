"""Google Sheets adapter placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import GoogleSheetsConfig


class GoogleSheetsAdapter(BaseAdapter):
    name = "sheets"

    def __init__(self, config: GoogleSheetsConfig) -> None:
        super().__init__(config)

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
            return ["Google Sheets inventory sheet ID missing; cannot sync metrics."]
        return [f"Updated {key} -> {value}" for key, value in metrics.items()]

    def implementation_notes(self) -> str:
        return (
            "Placeholder Google Sheets adapter; write operations are simulated pending API wiring."
        )
