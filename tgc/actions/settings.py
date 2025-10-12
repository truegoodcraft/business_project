"""View and edit controller settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class SettingsAction(SimpleAction):
    id: str = "7"
    name: str = "Settings & IDs"
    description: str = "View environment configuration and saved queries"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Load .env file values",
            "Mask sensitive tokens",
            "Display organization reference summary",
            "Provide editable guidance",
        ]
        notes = [
            "Update environment variables via .env.",
            "Run `python app.py --init-org` to edit organization details.",
        ]
        return self.render_plan(self.name, steps, notes=notes)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        masked = controller.mask_config()
        env_lines = [f"{key}: {value}" for key, value in masked.items()]
        org_lines = controller.organization_summary()

        log_lines: List[str] = ["Environment"] + env_lines + ["", "Organization"] + org_lines
        context.log_notes("settings", log_lines)

        plan_text = controller.build_plan(self.id)
        preview_lines = ["Environment:"] + env_lines + ["", "Organization:"] + org_lines
        notes = [
            "Environment settings displayed. Update .env manually to change values.",
            "Organization summary shown. Use `python app.py --init-org` for updates.",
        ]
        return ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=notes,
            preview="\n".join(preview_lines),
        )
