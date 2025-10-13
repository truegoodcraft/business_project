"""Sync basic metrics to Google Sheets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..controller import Controller
from ..integration_support import (
    format_sheets_missing_env_message,
    load_drive_module_config,
    service_account_email,
)
from ..modules.google_drive import DriveModuleConfig
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class SheetsSyncAction(SimpleAction):
    id: str = "4"
    name: str = "Sync metrics → Google Sheets"
    description: str = "Preview/push metrics to Google Sheets"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Collect metrics from staging data (simulated)",
            "Preview payload for Google Sheets",
            "Apply updates when confirmed",
        ]
        warnings: List[str] = []
        sheets = controller.adapters.get("sheets")
        if not sheets or not getattr(sheets, "is_configured", lambda: False)():
            warnings.append(self._missing_sheets_message(controller))
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        sheets = controller.adapters.get("sheets")
        payload: Dict[str, str] = {
            "total_inventory_items": "TBD",
            "pending_quotes": "TBD",
        }
        plan_text = controller.build_plan(self.id)
        configured = bool(sheets and getattr(sheets, "is_configured", lambda: False)())
        if not context.apply or not configured:
            message = self._missing_sheets_message(controller) if not configured else None
            if message:
                print(message)
            context.log_notes("sheets_preview", [str(payload)])
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message() + ([message] if message else []),
                preview=str(payload),
            )
        changes = getattr(sheets, "sync_metrics", lambda data: ["Sheets adapter missing."])(payload)
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=["Metrics synced to Google Sheets (simulated)."],
        )

    def _missing_sheets_message(self, controller: Controller) -> str:
        sheets = controller.adapters.get("sheets")
        if sheets and hasattr(sheets, "missing_configuration_message"):
            message = getattr(sheets, "missing_configuration_message")()
            if message:
                return message
        drive_module = controller.get_module("drive")
        drive_config = getattr(drive_module, "config", None)
        if isinstance(drive_config, DriveModuleConfig):
            email = service_account_email(drive_config)
        else:
            module_config = load_drive_module_config(controller.config.drive.module_config_path)
            email = service_account_email(module_config)
        return format_sheets_missing_env_message(email)
