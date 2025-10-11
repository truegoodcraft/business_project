"""View and edit settings."""

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
        return self.render_plan(
            self.name,
            steps,
            notes=[
                "Update environment variables via .env.",
                "Run `python app.py --init-org` to edit organization details.",
            ],
        )

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        masked = controller.mask_config()
        env_lines = [f"{key}: {value}" for key, value in masked.items()]
        org_lines = controller.organization_summary()
        context.log_notes("settings", ["Environment"] + env_lines + [""] + ["Organization"] + org_lines)
        plan_text = controller.build_plan(self.id)
        return ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=[
                "Environment settings displayed. Update .env manually to change values.",
                "Organization summary shown. Use `python app.py --init-org` for updates.",
            ],
            preview="\n".join(["Environment:"] + env_lines + ["", "Organization:"] + org_lines),
        )
