# SPDX-License-Identifier: AGPL-3.0-or-later
"""Interactive setup for the Google Drive module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..modules import GoogleDriveModule
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class DriveModuleAction(SimpleAction):
    id: str = "10"
    name: str = "Google Drive Module"
    description: str = "Configure sharing & validation"

    def build_plan(self, controller: Controller) -> str:
        module = controller.get_module("drive")
        warnings: List[str] = []
        if not isinstance(module, GoogleDriveModule):
            warnings.append("Drive module scaffolding not available.")
        steps = [
            "Display current Drive module status",
            "Optionally enable the module and capture Drive connection settings",
            "Store service-account credentials for reuse across sessions",
            "Persist configuration changes",
            "Optionally run a live Drive API connection test (honouring write-access settings)",
            "Optionally display stored configuration data",
        ]
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        plan_text = controller.build_plan(self.id)
        module_obj = controller.get_module("drive")
        if not isinstance(module_obj, GoogleDriveModule):
            error = "Google Drive module is not available."
            context.log_errors([error])
            return ActionResult(plan_text=plan_text, changes=[], errors=[error])

        status_lines_before = module_obj.status_summary()
        context.log_notes("drive_module_status", status_lines_before)

        if not context.apply:
            preview = "\n".join(status_lines_before)
            notes = self._dry_run_message() + ["Review the preview for current status details."]
            return ActionResult(plan_text=plan_text, changes=[], errors=[], notes=notes, preview=preview)

        changes, notes = module_obj.configure_interactive()
        errors: List[str] = []

        if changes:
            module_obj.save()
            context.log_changes(changes)
        else:
            notes.append("No configuration changes were made.")

        status_lines_after = module_obj.status_summary()
        preview_lines = status_lines_after
        if module_obj.is_enabled():
            if _prompt_yes_no("Test the Google Drive connection now?", default=True):
                success, messages = module_obj.test_connection()
                context.log_notes("drive_module_connection", messages)
                if success:
                    notes.append("Connection test succeeded.")
                else:
                    errors.extend(messages)
                    notes.append("Connection test failed; review errors for details.")
            if _prompt_yes_no("Display the stored Google Drive module data?", default=False):
                preview_lines = module_obj.preview_data()
                context.log_notes("drive_module_data", preview_lines)
        else:
            preview_lines = status_lines_after

        preview = "\n".join(preview_lines)
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=errors,
            notes=notes,
            preview=preview,
        )


def _prompt_yes_no(message: str, default: bool = False) -> bool:
    if default:
        suffix = " [Y/n]"
    else:
        suffix = " [y/N]"
    prompt = f"{message}{suffix}: "
    while True:
        answer = input(prompt).strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")
