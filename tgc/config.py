"""Configuration loading and masking helpers for the True Good Craft controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class NotionConfig:
    token: Optional[str] = None
    inventory_database_id: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.token and self.inventory_database_id)


@dataclass
class GoogleDriveConfig:
    root_folder_id: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.root_folder_id)


@dataclass
class GoogleSheetsConfig:
    inventory_sheet_id: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.inventory_sheet_id)


@dataclass
class GmailConfig:
    query: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.query)


@dataclass
class WaveConfig:
    graphql_token: Optional[str] = None
    business_id: Optional[str] = None
    sheet_id: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.graphql_token and self.business_id) or bool(self.sheet_id)


@dataclass
class AppConfig:
    notion: NotionConfig = field(default_factory=NotionConfig)
    drive: GoogleDriveConfig = field(default_factory=GoogleDriveConfig)
    sheets: GoogleSheetsConfig = field(default_factory=GoogleSheetsConfig)
    gmail: GmailConfig = field(default_factory=GmailConfig)
    wave: WaveConfig = field(default_factory=WaveConfig)
    reports_dir: Path = Path("reports")

    @classmethod
    def load(cls, env_file: str = ".env") -> "AppConfig":
        """Load configuration from ``env_file`` and environment variables."""
        _load_env_file(env_file)
        notion = NotionConfig(
            token=_clean_env("NOTION_TOKEN"),
            inventory_database_id=_clean_env("NOTION_DB_INVENTORY_ID"),
        )
        drive = GoogleDriveConfig(root_folder_id=_clean_env("DRIVE_ROOT_FOLDER_ID"))
        sheets = GoogleSheetsConfig(inventory_sheet_id=_clean_env("SHEET_INVENTORY_ID"))
        gmail = GmailConfig(query=_clean_env("GMAIL_QUERY"))
        wave = WaveConfig(
            graphql_token=_clean_env("WAVE_GRAPHQL_TOKEN"),
            business_id=_clean_env("WAVE_BUSINESS_ID"),
            sheet_id=_clean_env("WAVE_SHEET_ID"),
        )
        return cls(notion=notion, drive=drive, sheets=sheets, gmail=gmail, wave=wave)

    def enabled_modules(self) -> Dict[str, bool]:
        """Return a mapping of module names to their configuration status."""
        return {
            "notion": self.notion.is_configured(),
            "drive": self.drive.is_configured(),
            "sheets": self.sheets.is_configured(),
            "gmail": self.gmail.is_configured(),
            "wave": self.wave.is_configured(),
        }

    def mask_sensitive(self) -> Dict[str, Optional[str]]:
        """Return a masked view of sensitive config values for display purposes."""
        return {
            "NOTION_TOKEN": mask_secret(self.notion.token),
            "NOTION_DB_INVENTORY_ID": mask_secret(self.notion.inventory_database_id),
            "SHEET_INVENTORY_ID": mask_secret(self.sheets.inventory_sheet_id),
            "DRIVE_ROOT_FOLDER_ID": mask_secret(self.drive.root_folder_id),
            "GMAIL_QUERY": self.gmail.query,
            "WAVE_GRAPHQL_TOKEN": mask_secret(self.wave.graphql_token),
            "WAVE_BUSINESS_ID": mask_secret(self.wave.business_id),
            "WAVE_SHEET_ID": mask_secret(self.wave.sheet_id),
        }


def mask_secret(value: Optional[str]) -> Optional[str]:
    """Mask a secret value, keeping the first and last 3 characters visible."""
    if not value:
        return value
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"


def _load_env_file(env_file: str) -> None:
    path = Path(env_file)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _clean_env(key: str) -> Optional[str]:
    value = os.getenv(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


import os  # noqa: E402  # pylint: disable=wrong-import-position
