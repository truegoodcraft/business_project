"""Discover & Audit action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class DiscoverAuditAction(SimpleAction):
    id: str = "1"
    name: str = "Discover & Audit"
    description: str = "Read-only audit of configured adapters"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Check availability of each adapter",
            "Summarize capabilities and configuration gaps",
            "Produce audit report in reports directory",
        ]
        warnings: List[str] = []
        for key, ready in controller.adapter_status().items():
            if not ready:
                warnings.append(f"{key} adapter not configured; will be skipped.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        lines: List[str] = []
        notes: List[str] = []
        for key, adapter in controller.adapters.items():
            capability_lines = getattr(adapter, "describe_capabilities", lambda: [])()
            lines.append(f"Adapter: {key}")
            lines.extend(f"  - {line}" for line in capability_lines)
            metadata = getattr(adapter, "metadata", lambda: {})()
            if metadata:
                notes.append(f"{key} metadata: {metadata}")
            if key == "notion" and hasattr(adapter, "verify_inventory_access"):
                access = adapter.verify_inventory_access()
                status = access.get("status")
                detail = access.get("detail")
                if status:
                    lines.append(f"  - Inventory access status: {status}")
                if detail:
                    lines.append(f"    detail: {detail}")
                preview = access.get("preview_sample")
                if isinstance(preview, list):
                    lines.append(f"    preview rows available: {len(preview)}")
            if key == "drive":
                from ..modules import GoogleDriveModule

                module_obj = controller.get_module("drive")
                if isinstance(module_obj, GoogleDriveModule):
                    validation_lines = module_obj.validation_summary()
                    if validation_lines:
                        lines.append("  - Drive module validation:")
                        lines.extend(f"    {line}" for line in validation_lines)
                    details = module_obj.validation_details()
                    for message in details.get("errors", []):
                        notes.append(f"drive validation error: {message}")
                    notes.extend(
                        f"drive validation note: {message}" for message in details.get("notes", [])
                    )
        context.log_notes("audit", lines)
        plan_text = controller.build_plan(self.id)
        return ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=notes or self._dry_run_message(),
            preview="\n".join(lines),
        )
