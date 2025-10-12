"""Action for building the Master Index reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..controller import Controller
from ..master_index_controller import MasterIndexController, TraversalLimits
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class MasterIndexAction(SimpleAction):
    id: str = "12"
    name: str = "Build Master Index — Notion pages & Drive files → Markdown"
    description: str = "Generate Markdown indexes for configured Notion pages and Drive files"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Verify Notion and Google Drive adapters are ready",
            "Read configured Notion root pages and traverse descendants",
            "Walk Google Drive roots, resolving shortcuts and collecting metadata",
            "Render canonical Markdown tables and write reports (apply only)",
        ]
        warnings: List[str] = []
        statuses = controller.adapter_status()
        if not statuses.get("notion", False):
            warnings.append("Notion adapter is not ready; run Discover & Audit first.")
        if not statuses.get("drive", False):
            warnings.append("Drive adapter is not ready; run Discover & Audit first.")
        return self.render_plan(self.name, steps, warnings=warnings or None)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        plan_text = controller.build_plan(self.id)
        master = MasterIndexController(controller)
        limits = self._limits_from_context(context)
        summary = master.run_master_index(dry_run=not context.apply, limits=limits)

        notion_count = int(summary.get("notion_count", 0))
        drive_count = int(summary.get("drive_count", 0))
        output_dir = summary.get("output_dir")
        status = summary.get("status", "unknown")
        message = summary.get("message")

        lines = [
            f"status: {status}",
            f"dry_run: {summary.get('dry_run')}",
            f"notion_count: {notion_count}",
            f"drive_count: {drive_count}",
            f"output_dir: {output_dir or '(not written)'}",
        ]
        if message:
            lines.append(f"message: {message}")
        context.log_notes("master_index_summary", lines)

        notion_errors = [str(value) for value in summary.get("notion_errors", [])]
        drive_errors = [str(value) for value in summary.get("drive_errors", [])]

        if summary.get("status") == "unavailable":
            detail = message or "Master Index unavailable: run 'Discover & Audit' and verify Notion + Drive readiness."
            errors = [detail]
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=errors,
                notes=self._dry_run_message(),
            )

        errors = notion_errors + drive_errors
        if summary.get("status") == "error":
            if not errors:
                errors = [message or "Unable to initialise Master Index modules."]
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=errors,
                notes=self._dry_run_message(),
            )

        if notion_errors or drive_errors:
            context.log_notes("master_index_warnings", notion_errors + drive_errors)

        print(f"Notion pages: {notion_count}")
        print(f"Drive files: {drive_count}")
        if output_dir:
            print(f"Outputs: {output_dir}")
        if message:
            print(message)

        notes: List[str] = []
        changes: List[str] = []

        if context.apply:
            notion_path = summary.get("notion_output")
            drive_path = summary.get("drive_output")
            if notion_path:
                changes.append(f"Wrote Notion index to {notion_path}")
            if drive_path:
                changes.append(f"Wrote Drive index to {drive_path}")
        else:
            notes.extend(self._dry_run_message())
            if output_dir:
                notes.append(f"Planned output directory: {output_dir}")

        for warning in notion_errors:
            notes.append(f"Notion warning: {warning}")
        for warning in drive_errors:
            notes.append(f"Drive warning: {warning}")

        notes.append(f"Indexed Notion pages: {notion_count}")
        notes.append(f"Indexed Drive files: {drive_count}")
        if message:
            notes.append(f"Message: {message}")

        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=notes,
        )

    def _limits_from_context(self, context: RunContext) -> Optional[TraversalLimits]:
        options = getattr(context, "options", {}) or {}
        if not options:
            return None

        def _positive(value: object, caster) -> Optional[float]:
            if value is None:
                return None
            try:
                numeric = caster(value)
            except (TypeError, ValueError):
                return None
            return numeric if numeric > 0 else None

        seconds = _positive(options.get("max_seconds"), float)
        pages = _positive(options.get("max_pages"), int)
        requests = _positive(options.get("max_requests"), int)
        depth = _positive(options.get("max_depth"), int)

        if not any(value is not None for value in (seconds, pages, requests, depth)):
            return None

        return TraversalLimits(
            max_seconds=seconds,
            max_pages=int(pages) if pages is not None else None,
            max_requests=int(requests) if requests is not None else None,
            max_depth=int(depth) if depth is not None else None,
        )
