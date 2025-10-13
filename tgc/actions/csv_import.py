"""Import CSV to inventory action."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class CsvImportAction(SimpleAction):
    id: str = "3"
    name: str = "Import CSV → Inventory"
    description: str = "Map CSV columns into inventory fields"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Load CSV file from ./staging/inventory.csv (or prompt for path)",
            "Map columns to {name, sku, qty, batch, notes}",
            "Generate preview and optional apply",
            "Write staged updates to reports",
        ]
        warnings: List[str] = []
        notion = controller.adapters.get("notion")
        if not notion or not getattr(notion, "is_configured", lambda: False)():
            warnings.append("Notion adapter not configured; will run in preview-only mode.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        notion = controller.adapters.get("notion")
        plan_text = controller.build_plan(self.id)
        staging_path = Path("staging/inventory.csv")
        notes = [f"Expected staging CSV at {staging_path.resolve()}"]
        if not staging_path.exists():
            notes.append("Staging CSV not found; provide file before applying.")
        if not context.apply or not notion or not getattr(notion, "is_configured", lambda: False)():
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=notes + self._dry_run_message(),
                preview="CSV import preview requires staging file.",
            )
        # Placeholder apply logic
        changes = getattr(notion, "stage_inventory_updates", lambda rows: ["No Notion adapter available."])(
            []
        )
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=notes + ["CSV processed (simulated)."],
        )
