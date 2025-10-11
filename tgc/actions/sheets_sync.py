"""Sync basic metrics to Google Sheets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class SheetsSyncAction(SimpleAction):
    id: str = "4"
    name: str = "Sync metrics → Google Sheets"
    description: str = "Preview and optionally push metrics to dashboard sheet"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Collect metrics from staging data (simulated)",
            "Preview payload for Google Sheets",
            "Apply updates when confirmed",
        ]
        warnings: List[str] = []
        sheets = controller.adapters.get("sheets")
        if not sheets or not getattr(sheets, "is_configured", lambda: False)():
            warnings.append("Google Sheets adapter not configured; preview only.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        sheets = controller.adapters.get("sheets")
        payload: Dict[str, str] = {
            "total_inventory_items": "TBD",
            "pending_quotes": "TBD",
        }
        plan_text = controller.build_plan(self.id)
        if not context.apply or not sheets or not getattr(sheets, "is_configured", lambda: False)():
            context.log_notes("sheets_preview", [str(payload)])
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview=str(payload),
            )
        changes = getattr(sheets, "sync_metrics", lambda data: ["Sheets adapter missing."])(payload)
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=["Metrics synced to Google Sheets (simulated)."],
        )
