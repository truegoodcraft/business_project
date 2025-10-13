"""Action for building the Master Index reports."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.capabilities import REGISTRY
from core import retention
from core.plugin_api import Result
from core.runtime import run_capability
from core.unilog import write as uni_write

from ..controller import Controller
from ..master_index_controller import MasterIndexController, TraversalLimits
from ..reporting import ActionResult, RunContext
from .base import SimpleAction
from .sheets_index import build_sheets_index, write_sheets_index_markdown


def _normalise_sheets_payload(payload: Any, errors: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, Result):
        if payload.ok:
            return _normalise_sheets_payload(payload.data, errors)
        errors.extend(payload.notes or ["Sheets capability failed"])
        return _normalise_sheets_payload(payload.data, errors) if payload.data else []
    if isinstance(payload, list):
        rows: List[Dict[str, Any]] = []
        for row in payload:
            if isinstance(row, dict):
                rows.append(dict(row))
            else:
                try:
                    rows.append(dict(row))
                except Exception:
                    continue
        return rows
    if isinstance(payload, dict):
        rows_value = payload.get("rows")
        if isinstance(rows_value, list):
            return _normalise_sheets_payload(rows_value, errors)
        data_value = payload.get("data")
        if isinstance(data_value, list):
            return _normalise_sheets_payload(data_value, errors)
    return []


@dataclass
class MasterIndexAction(SimpleAction):
    id: str = "12"
    name: str = "Build Master Index — Notion, Drive, (Sheets) → Markdown"
    description: str = "Generate Markdown indexes for configured Notion, Drive, and Sheets sources"

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
        summary = master.run_master_index(
            dry_run=not context.apply, limits=limits, run_context=context
        )

        notion_count = int(summary.get("notion_count", 0))
        drive_count = int(summary.get("drive_count", 0))
        output_dir = summary.get("output_dir")
        output_dir_path = Path(output_dir) if output_dir else None
        status = summary.get("status", "unknown")
        message = summary.get("message")
        mode = "apply" if context.apply else "dry_run"

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
            uni_write(
                "master_index.result",
                context.run_id,
                mode=mode,
                notion_count=notion_count,
                drive_count=drive_count,
                sheets_tabs=0,
                output_dir=str(output_dir) if output_dir else None,
                ok=False,
                errors_count=len(errors),
            )
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
            uni_write(
                "master_index.result",
                context.run_id,
                mode=mode,
                notion_count=notion_count,
                drive_count=drive_count,
                sheets_tabs=0,
                output_dir=str(output_dir) if output_dir else None,
                ok=False,
                errors_count=len(errors),
            )
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
        sheets_errors: List[str] = []
        sheets_notes: List[str] = []
        sheets_changes: List[str] = []
        sheets_rows: List[Dict[str, Any]] = []

        if context.apply:
            notion_path = summary.get("notion_output")
            drive_path = summary.get("drive_output")
            drive_chunks = [
                str(value)
                for value in summary.get("drive_outputs", [])
                if isinstance(value, str) and value
            ]
            if notion_path:
                changes.append(f"Wrote Notion index to {notion_path}")
            if drive_chunks:
                for path in drive_chunks:
                    changes.append(f"Wrote Drive index to {path}")
            elif drive_path:
                changes.append(f"Wrote Drive index to {drive_path}")

            drive_module = controller.get_module("drive")
            root_ids: List[str] = []
            if drive_module is not None:
                candidate = getattr(drive_module, "root_ids", None)
                if callable(candidate):
                    try:
                        root_ids = [value for value in candidate() if value]
                    except Exception as exc:  # pragma: no cover - defensive
                        sheets_errors.append(f"Unable to load Drive roots for Sheets index: {exc}")
            if not root_ids:
                fallback_root = getattr(controller.config.drive, "fallback_root_id", None)
                if fallback_root:
                    root_ids = [fallback_root]

            used_capability = False
            if root_ids:
                if "google.sheets_index" in REGISTRY:
                    try:
                        payload = run_capability(
                            "google.sheets_index",
                            root_ids=root_ids,
                            config=controller.config,
                            limits=limits,
                        )
                    except PermissionError as exc:
                        sheets_errors.append(str(exc))
                    else:
                        rows = _normalise_sheets_payload(payload, sheets_errors)
                        sheets_rows.extend(rows)
                        used_capability = True
                if not used_capability:
                    for root_id in root_ids:
                        try:
                            sheets_rows.extend(
                                build_sheets_index(limits, root_id, controller.config)
                            )
                        except Exception as exc:
                            sheets_errors.append(
                                f"Sheets index traversal failed for Drive root {root_id}: {exc}"
                            )
            else:
                sheets_notes.append(
                    "Sheets index skipped: no Drive root IDs configured for traversal."
                )

            if output_dir_path:
                try:
                    sheet_paths = write_sheets_index_markdown(output_dir_path, sheets_rows)
                except OSError as exc:
                    sheets_errors.append(f"Failed to write Sheets index: {exc}")
                else:
                    for path in sheet_paths:
                        sheets_changes.append(f"Wrote Sheets index to {path}")
            elif sheets_rows and not output_dir_path:
                sheets_errors.append(
                    "Sheets index rows generated but output directory was not provided."
                )
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
        if sheets_notes:
            notes.extend(sheets_notes)
        if sheets_changes:
            changes.extend(sheets_changes)
        if sheets_errors:
            for warning in sheets_errors:
                notes.append(f"Sheets warning: {warning}")
        if message:
            notes.append(f"Message: {message}")

        action_result = ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=[],
            notes=notes,
        )

        if context.apply and retention.retention_enabled():
            status_value = summary.get("status")
            if status_value not in {"error", "unavailable"}:
                verbose = logging.getLogger().isEnabledFor(logging.DEBUG)
                try:
                    retention.prune_old_runs(
                        dry_run=False,
                        current_run_id=context.run_id,
                        verbose=verbose,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    from core.unilog import write as log_event

                    log_event("retention.error", None, path="auto", error=str(exc))
                    if verbose:
                        print(f"Retention auto-run failed: {exc}")

        sheets_tabs_count = len(sheets_rows)
        errors_count = len(notion_errors) + len(drive_errors) + len(sheets_errors)
        uni_write(
            "master_index.result",
            context.run_id,
            mode=mode,
            notion_count=notion_count,
            drive_count=drive_count,
            sheets_tabs=sheets_tabs_count,
            output_dir=str(output_dir_path) if output_dir_path else output_dir,
            ok=(errors_count == 0),
            errors_count=errors_count,
        )

        return action_result

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
