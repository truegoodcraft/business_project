# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gmail adapter placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import GmailConfig


class GmailAdapter(BaseAdapter):
    name = "gmail"

    def __init__(self, config: GmailConfig) -> None:
        super().__init__(config)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability(
                name="Quote import",
                description="Parse vendor quotes and stage data",
                configured=self.is_configured(),
            )
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {"query": self.config.query}

    def preview_import(self) -> Dict[str, Optional[str]]:
        if not self.is_configured():
            return {"status": "Gmail query not configured."}
        return {
            "status": "ready",
            "query": self.config.query,
            "estimated_messages": "TBD (requires API integration)",
        }

    def import_messages(self) -> List[str]:
        if not self.is_configured():
            return ["Cannot import: Gmail query missing."]
        return [
            "Fetched messages using configured query (simulated)",
            "Extracted attachments and metadata for staging",
        ]

    def implementation_notes(self) -> str:
        return (
            "Placeholder Gmail adapter; message parsing and API calls are simulated for now."
        )
