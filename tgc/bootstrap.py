"""Bootstrap helpers to build the controller and adapters."""

from __future__ import annotations

from typing import Dict

from .actions import (
    ContactsAction,
    CsvImportAction,
    DiscoverAuditAction,
    DriveLinkAction,
    GmailImportAction,
    LogsAction,
    SettingsAction,
    SheetsSyncAction,
    DriveModuleAction,
    GmailImportAction,
    LogsAction,
    NotionModuleAction,
    SettingsAction,
    SheetsSyncAction,
    UpdateAction,
    WaveAction,
)
from .adapters import GmailAdapter, GoogleDriveAdapter, GoogleSheetsAdapter, NotionAdapter, WaveAdapter
from .config import AppConfig
from .controller import Controller
from .organization import OrganizationProfile
from .controller import Controller
from .modules import GoogleDriveModule
from .notion import NotionAccessModule


def bootstrap_controller(env_file: str = ".env") -> Controller:
    """Build a controller with adapters and register default actions."""
    config = AppConfig.load(env_file)
    adapters = _build_adapters(config)
    controller = Controller(config=config, adapters=adapters, reports_root=config.reports_dir)
    modules = _build_modules(config, env_file)
    organization = OrganizationProfile.load()
    organization.ensure_reference_page()
    modules = _build_modules()
    controller = Controller(
        config=config,
        adapters=adapters,
        organization=organization,
        reports_root=config.reports_dir,
        modules=modules,
    )
    _register_actions(controller)
    return controller


def _build_adapters(config: AppConfig) -> Dict[str, object]:
    return {
        "notion": NotionAdapter(config.notion),
        "drive": GoogleDriveAdapter(config.drive),
        "sheets": GoogleSheetsAdapter(config.sheets),
        "gmail": GmailAdapter(config.gmail),
        "wave": WaveAdapter(config.wave),
    }


def _register_actions(controller: Controller) -> None:
def _build_modules() -> Dict[str, object]:
    return {
        "drive": GoogleDriveModule.load(),
def _build_modules(config: AppConfig, env_file: str) -> Dict[str, object]:
    return {
        "notion_access": NotionAccessModule(config.notion, env_file),
    }


def _register_actions(controller: Controller) -> None:
    controller.register_action(UpdateAction())
    controller.register_action(DiscoverAuditAction())
    controller.register_action(GmailImportAction())
    controller.register_action(CsvImportAction())
    controller.register_action(SheetsSyncAction())
    controller.register_action(DriveLinkAction())
    controller.register_action(DriveModuleAction())
    controller.register_action(ContactsAction())
    controller.register_action(SettingsAction())
    controller.register_action(LogsAction())
    controller.register_action(WaveAction())
    controller.register_action(NotionModuleAction())
