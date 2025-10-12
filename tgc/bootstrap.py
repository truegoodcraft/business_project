"""Bootstrap helpers to build the controller and adapters."""

from __future__ import annotations

from typing import Dict

from .actions import (
    ContactsAction,
    CsvImportAction,
    DiscoverAuditAction,
    DriveLinkAction,
    DriveModuleAction,
    GmailImportAction,
    LogsAction,
    MasterIndexAction,
    NotionModuleAction,
    SettingsAction,
    SheetsSyncAction,
    UpdateAction,
    WaveAction,
)
from .adapters import GmailAdapter, GoogleDriveAdapter, GoogleSheetsAdapter, NotionAdapter, WaveAdapter
from .config import AppConfig
from .controller import Controller
from .integration_support import load_drive_module_config, service_account_email
from .modules import GoogleDriveModule
from .modules.google_drive import DriveModuleConfig
from .notion import NotionAccessModule
from .organization import OrganizationProfile


def bootstrap_controller(env_file: str = ".env") -> Controller:
    """Build a controller with adapters, modules, and default actions."""

    config = AppConfig.load(env_file)
    drive_module_config = load_drive_module_config(config.drive.module_config_path)
    adapters = _build_adapters(config, drive_module_config)
    organization = OrganizationProfile.load()
    organization.ensure_reference_page()
    modules = _build_modules(config, env_file, drive_module_config)
    controller = Controller(
        config=config,
        adapters=adapters,
        organization=organization,
        reports_root=config.reports_dir,
        modules=modules,
    )
    _register_actions(controller)
    return controller


def _build_adapters(config: AppConfig, drive_module_config: DriveModuleConfig) -> Dict[str, object]:
    sheets_email = service_account_email(drive_module_config)
    return {
        "notion": NotionAdapter(config.notion),
        "drive": GoogleDriveAdapter(config.drive),
        "sheets": GoogleSheetsAdapter(
            config.sheets,
            drive_module_config,
            service_account_email=sheets_email,
        ),
        "gmail": GmailAdapter(config.gmail),
        "wave": WaveAdapter(config.wave),
    }


def _build_modules(
    config: AppConfig, env_file: str, drive_module_config: DriveModuleConfig
) -> Dict[str, object]:
    return {
        "drive": GoogleDriveModule(
            drive_module_config,
            config.drive.module_config_path.expanduser(),
            fallback_root_id=config.drive.fallback_root_id,
            shared_drive_id=config.drive.shared_drive_id,
        ),
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
    controller.register_action(MasterIndexAction())
