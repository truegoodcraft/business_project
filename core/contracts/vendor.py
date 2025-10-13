"""Vendor contracts used for inventory coordination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .common import ID


@dataclass
class Vendor:
    """Serializable vendor record."""

    id: ID
    name: str
    email: Optional[str]
    phone: Optional[str]
    drive_folder_id: Optional[str]
    notion_page_id: Optional[str]

    def __post_init__(self) -> None:
        if not isinstance(self.id, ID):
            raise TypeError("id must be an ID instance")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        for attr in ("email", "phone", "drive_folder_id", "notion_page_id"):
            value = getattr(self, attr)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{attr} must be a string or None")
