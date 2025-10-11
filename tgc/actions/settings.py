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
            "Display editable guidance",
        ]
        return self.render_plan(self.name, steps, notes=["Edit .env directly or via future prompts."])

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        masked = controller.mask_config()
        lines = [f"{key}: {value}" for key, value in masked.items()]
        context.log_notes("settings", lines)
        plan_text = controller.build_plan(self.id)
        return ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=["Settings displayed. Update .env manually to change values."],
            preview="\n".join(lines),
        )
