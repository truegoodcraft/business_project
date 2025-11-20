# SPDX-License-Identifier: AGPL-3.0-or-later
"""Link Drive PDFs to Notion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class DriveLinkAction(SimpleAction):
    id: str = "5"
    name: str = "Link Drive PDFs to Notion"
    description: str = "Match and attach Drive PDFs to inventory items"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Scan Drive for PDFs matching quote_{vendor}_{date}_{ref}.pdf",
            "Resolve references to Notion inventory items",
            "Preview linking operations",
        ]
        warnings: List[str] = []
        drive = controller.adapters.get("drive")
        notion = controller.adapters.get("notion")
        if not drive or not getattr(drive, "is_configured", lambda: False)():
            warnings.append("Drive adapter not configured; cannot scan files.")
        if not notion or not getattr(notion, "is_configured", lambda: False)():
            warnings.append("Notion adapter not configured; cannot attach links.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        plan_text = controller.build_plan(self.id)
        drive = controller.adapters.get("drive")
        notion = controller.adapters.get("notion")
        if not drive or not getattr(drive, "is_configured", lambda: False)() or not notion or not getattr(notion, "is_configured", lambda: False)():
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=["Drive or Notion adapter not configured."],
                notes=self._dry_run_message(),
            )
        if not context.apply:
            preview = [
                "Would match files and produce linking table (simulated)",
            ]
            context.log_notes("drive_link_preview", preview)
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview="\n".join(preview),
            )
        matches = [
            {"filename": "quote_vendor_20240101_123.pdf", "sku": "SKU-123"},
        ]
        change_lines = getattr(drive, "link_pdfs", lambda rows: ["Drive adapter missing."])(matches)
        context.log_notes("drive_link", change_lines)
        return ActionResult(
            plan_text=plan_text,
            changes=change_lines,
            errors=[],
            notes=["Links applied in Notion (simulated)."],
        )
