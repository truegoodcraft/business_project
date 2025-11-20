# SPDX-License-Identifier: AGPL-3.0-or-later
"""Import Gmail quotes action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class GmailImportAction(SimpleAction):
    id: str = "2"
    name: str = "Import from Gmail"
    description: str = "Stage vendor quotes/orders (optional)"

    def build_plan(self, controller: Controller) -> str:
        gmail = controller.adapters.get("gmail")
        steps = [
            "Load Gmail adapter with configured query",
            "Fetch matching messages and attachments",
            "Normalize to staging records and write to reports",
        ]
        warnings: List[str] = []
        if not gmail or not getattr(gmail, "is_configured", lambda: False)():
            warnings.append("Gmail adapter not configured; import will be skipped.")
        else:
            preview = getattr(gmail, "preview_import", lambda: {"status": "unknown"})()
            warnings.append(f"Preview: {preview}")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        gmail = controller.adapters.get("gmail")
        if not gmail or not getattr(gmail, "is_configured", lambda: False)():
            return ActionResult(
                plan_text=controller.build_plan(self.id),
                changes=[],
                errors=["Gmail adapter not configured."],
                notes=self._dry_run_message(),
            )
        plan_text = controller.build_plan(self.id)
        if not context.apply:
            preview = getattr(gmail, "preview_import", lambda: {})()
            context.log_notes("gmail_preview", [str(preview)])
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview=str(preview),
            )
        changes = getattr(gmail, "import_messages", lambda: ["No importer defined."])()
        context.log_notes("gmail_import", changes)
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=["Messages staged under reports directory."],
        )
