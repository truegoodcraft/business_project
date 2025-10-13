"""Discover & Audit action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from core.signing import SIGNING_AVAILABLE
from core.unilog import write as uni_write

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class DiscoverAuditAction(SimpleAction):
    id: str = "1"
    name: str = "Discover & Audit"
    description: str = "Read-only adapter audit"

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
        lines.append("Security / Validation:")
        if SIGNING_AVAILABLE:
            lines.append("  - Plugin signing: enabled (Ed25519)")
            plugin_signing_status = "enabled"
        else:
            lines.append("  - Plugin signing: disabled (PyNaCl not installed)")
            plugin_signing_status = "disabled"
        notes: List[str] = []
        warnings_list: List[str] = []
        errors_list: List[str] = []
        adapter_status = controller.adapter_status()
        for name, ready in adapter_status.items():
            if not ready:
                warnings_list.append(f"{name} adapter not ready")

        notion_status_dict: Dict[str, object] = {
            "adapter_ready": bool(adapter_status.get("notion")),
        }
        drive_status_dict: Dict[str, object] = {
            "adapter_ready": bool(adapter_status.get("drive")),
            "validation_errors": 0,
            "validation_notes": 0,
        }
        sheets_status_dict: Dict[str, object] = {
            "adapter_ready": bool(adapter_status.get("sheets")),
        }

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
                    notion_status_dict["inventory_status"] = status
                if detail:
                    lines.append(f"    detail: {detail}")
                    notion_status_dict["inventory_detail"] = detail
                preview = access.get("preview_sample")
                if isinstance(preview, list):
                    lines.append(f"    preview rows available: {len(preview)}")
                    notion_status_dict["preview_rows"] = len(preview)
            if key == "drive":
                from ..modules import GoogleDriveModule

                module_obj = controller.get_module("drive")
                if isinstance(module_obj, GoogleDriveModule):
                    validation_lines = module_obj.validation_summary()
                    if validation_lines:
                        lines.append("  - Drive module validation:")
                        lines.extend(f"    {line}" for line in validation_lines)
                        drive_status_dict["validation_summary"] = validation_lines
                    details = module_obj.validation_details()
                    for message in details.get("errors", []):
                        notes.append(f"drive validation error: {message}")
                        errors_list.append(str(message))
                    notes.extend(
                        f"drive validation note: {message}" for message in details.get("notes", [])
                    )
                    drive_status_dict["validation_errors"] = len(details.get("errors", []))
                    drive_status_dict["validation_notes"] = len(details.get("notes", []))
        context.log_notes("audit", lines)
        plan_text = controller.build_plan(self.id)
        result = ActionResult(
            plan_text=plan_text,
            changes=[],
            errors=[],
            notes=notes or self._dry_run_message(),
            preview="\n".join(lines),
        )
        uni_write(
            "discover_audit.result",
            context.run_id,
            security={"plugin_signing": plugin_signing_status},
            notion=notion_status_dict,
            drive=drive_status_dict,
            sheets=sheets_status_dict,
            warnings=warnings_list,
            errors=errors_list,
        )
        return result
