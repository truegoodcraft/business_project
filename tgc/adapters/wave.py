"""Optional Wave accounting adapter placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import WaveConfig


class WaveAdapter(BaseAdapter):
    name = "wave"

    def __init__(self, config: WaveConfig) -> None:
        super().__init__(config)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        configured = self.is_configured()
        return [
            AdapterCapability(
                name="GraphQL API",
                description="Pull transactions and balances",
                configured=bool(self.config.graphql_token and self.config.business_id),
            ),
            AdapterCapability(
                name="Wave Sheets",
                description="Read via Google Sheets bridge",
                configured=bool(self.config.sheet_id),
            ),
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {
            "business_id": self.config.business_id,
            "sheet_id": self.config.sheet_id,
        }

    def discover_financials(self) -> List[str]:
        if not self.is_configured():
            return ["Wave adapter not configured; skipping."]
        lines = ["Wave discovery (simulated):"]
        if self.config.graphql_token and self.config.business_id:
            lines.append("- Would call GraphQL API for account balances")
        if self.config.sheet_id:
            lines.append("- Would read data from Wave Sheets connector")
        return lines
