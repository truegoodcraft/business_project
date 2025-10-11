"""Configuration loading and masking helpers for the controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class NotionConfig:
    module_enabled: bool = False
    token: Optional[str] = None
    inventory_database_id: Optional[str] = None
    root_ids: List[str] = field(default_factory=list)
    page_size: int = 100
    include_comments: bool = False
    include_file_metadata: bool = True
    max_depth: int = 0
    rate_limit_qps: float = 3.0
    timeout_seconds: int = 30
    allowlist_ids: List[str] = field(default_factory=list)
    denylist_ids: List[str] = field(default_factory=list)

    def is_configured(self) -> bool:
        if not self.module_enabled:
            return False
        has_token = bool(self.token)
        has_roots = bool(self.root_ids or self.inventory_database_id)
        return bool(has_token and has_roots)


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
        api_key = _clean_env("NOTION_API_KEY")
        token = _clean_env("NOTION_TOKEN") or api_key
        notion = NotionConfig(
            module_enabled=_env_bool("NOTION_MODULE_ENABLED", default=False),
            token=token,
            inventory_database_id=_clean_env("NOTION_DB_INVENTORY_ID"),
            root_ids=_env_list("NOTION_ROOT_IDS"),
            page_size=_env_int("NOTION_PAGE_SIZE", default=100),
            include_comments=_env_bool("NOTION_INCLUDE_COMMENTS", default=False),
            include_file_metadata=_env_bool("NOTION_INCLUDE_FILE_METADATA", default=True),
            max_depth=_env_int("NOTION_MAX_DEPTH", default=0),
            rate_limit_qps=_env_float("NOTION_RATE_LIMIT_QPS", default=3.0),
            timeout_seconds=_env_int("NOTION_TIMEOUT_SECONDS", default=30),
            allowlist_ids=_env_list("NOTION_ALLOWLIST_IDS"),
            denylist_ids=_env_list("NOTION_DENYLIST_IDS"),
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
            "NOTION_API_KEY": mask_secret(self.notion.token),
            "NOTION_DB_INVENTORY_ID": mask_secret(self.notion.inventory_database_id),
            "NOTION_ROOT_IDS": ",".join(self.notion.root_ids) or None,
            "NOTION_MODULE_ENABLED": str(self.notion.module_enabled).lower(),
            "NOTION_PAGE_SIZE": str(self.notion.page_size),
            "NOTION_INCLUDE_COMMENTS": str(self.notion.include_comments).lower(),
            "NOTION_INCLUDE_FILE_METADATA": str(self.notion.include_file_metadata).lower(),
            "NOTION_MAX_DEPTH": str(self.notion.max_depth),
            "NOTION_RATE_LIMIT_QPS": str(self.notion.rate_limit_qps),
            "NOTION_TIMEOUT_SECONDS": str(self.notion.timeout_seconds),
            "NOTION_ALLOWLIST_IDS": ",".join(self.notion.allowlist_ids) or None,
            "NOTION_DENYLIST_IDS": ",".join(self.notion.denylist_ids) or None,
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


def _env_bool(key: str, default: bool = False) -> bool:
    value = _clean_env(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int = 0) -> int:
    value = _clean_env(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    value = _clean_env(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_list(key: str) -> List[str]:
    value = _clean_env(key)
    if value is None:
        return []
    parts = [part.strip() for part in value.split(",")]
    return [part for part in parts if part]


import os  # noqa: E402  # pylint: disable=wrong-import-position
