# SPDX-License-Identifier: AGPL-3.0-or-later
"""Logs & Reports action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class LogsAction(SimpleAction):
    id: str = "8"
    name: str = "Logs & Reports"
    description: str = "List recent run directories"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "List runs from reports directory",
            "Show latest run summary",
            "Provide path hints for review",
        ]
        return self.render_plan(self.name, steps)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        runs = controller.list_reports()
        lines = [str(path) for path in runs[-5:]] or ["No runs yet."]
        context.log_notes("logs", lines)
        plan_text = controller.build_plan(self.id)
        return ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=["Logs listed. Open files manually for details."],
            preview="\n".join(lines),
        )
