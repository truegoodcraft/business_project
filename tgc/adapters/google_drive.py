"""Google Drive adapter placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import AdapterCapability, BaseAdapter
from ..config import GoogleDriveConfig


class GoogleDriveAdapter(BaseAdapter):
    name = "drive"

    def __init__(self, config: GoogleDriveConfig) -> None:
        super().__init__(config)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability(
                name="File lookup",
                description="Find and match PDFs by reference ID",
                configured=self.is_configured(),
            )
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {"root_folder_id": self.config.root_folder_id}

    def link_pdfs(self, references: List[Dict[str, str]]) -> List[str]:
        if not self.is_configured():
            return ["Drive root folder ID missing; cannot link PDFs."]
        return [
            f"Linked {ref.get('filename', 'file')} to inventory {ref.get('sku', '?')}"
            for ref in references
        ]
