"""Notion adapter placeholder implementation."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import NotionConfig


class NotionAdapter(BaseAdapter):
    name = "notion"

    def __init__(self, config: NotionConfig) -> None:
        super().__init__(config)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability(
                name="Inventory",
                description="Read/write inventory database entries by ID",
                configured=self.is_configured(),
            ),
            AdapterCapability(
                name="Contacts",
                description="Link contacts and vendors by GUID",
                configured=self.is_configured(),
            ),
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {
            "inventory_database_id": self.config.inventory_database_id,
        }

    # Placeholder operations -------------------------------------------------

    def audit_inventory(self) -> List[str]:
        if not self.is_configured():
            return ["Notion inventory database is not configured."]
        return [
            "Checked inventory database schema (simulated)",
            "Validated required properties: name, sku, qty, batch, notes",
        ]

    def stage_inventory_updates(self, rows: List[Dict[str, str]]) -> List[str]:
        if not self.is_configured():
            return ["Cannot stage inventory updates: Notion not configured."]
        return [f"Prepared update for SKU {row.get('sku','?')}" for row in rows]
