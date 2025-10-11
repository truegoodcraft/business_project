"""Contacts and vendors normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class ContactsAction(SimpleAction):
    id: str = "6"
    name: str = "Contacts/Vendors"
    description: str = "Normalize, dedupe, and link contacts"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Load contacts from staging sources (CSV, Gmail inferences)",
            "Normalize fields to canonical schema",
            "Dedupe by contact_guid and external IDs",
            "Write preview report",
        ]
        warnings: List[str] = []
        notion = controller.adapters.get("notion")
        if not notion or not getattr(notion, "is_configured", lambda: False)():
            warnings.append("Notion adapter missing; output will remain in staging.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        plan_text = controller.build_plan(self.id)
        preview_lines = [
            "Found 0 contacts (sample data)",
            "Ready to map to canonical schema",
        ]
        context.log_notes("contacts_preview", preview_lines)
        if not context.apply:
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview="\n".join(preview_lines),
            )
        notion = controller.adapters.get("notion")
        if not notion or not getattr(notion, "is_configured", lambda: False)():
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=["Notion adapter not configured; cannot apply contacts."],
                notes=self._dry_run_message(),
            )
        changes = ["Applied 0 contacts (simulated)"]
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=["Contacts synced to Notion (simulated)."],
        )
