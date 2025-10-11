"""Interactive management action for the Notion access module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..adapters import NotionAdapter
from ..controller import Controller
from ..reporting import ActionResult, RunContext
from ..notion import NotionAccessModule
from .base import SimpleAction


@dataclass
class NotionModuleAction(SimpleAction):
    id: str = "10"
    name: str = "Notion Access Module"
    description: str = "Enable, test, and inspect Notion connectivity"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Show current Notion module status",
            "Offer enable/disable commands",
            "Test connection and report simple metrics",
            "Preview sampled data on request",
        ]
        return self.render_plan(
            self.name,
            steps,
            notes=[
                "Module prompts run interactively.",
                "Outputs remain terse and in-character.",
            ],
        )

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        module = self._require_module(controller)
        plan_text = controller.build_plan(self.id)
        notes: List[str] = []
        changes: List[str] = []
        errors: List[str] = []

        self._emit_lines(module.status_lines(), notes)

        while True:
            try:
                command = input("COMMAND [enable/disable/test/show/quit]: ").strip().lower()
            except KeyboardInterrupt:  # pragma: no cover - interactive safety
                print("INFO: command cancelled.")
                notes.append("INFO: command cancelled.")
                break
            if command in {"", "quit", "q", "exit"}:
                print("STATE: exiting module menu.")
                notes.append("STATE: exiting module menu.")
                break
            if command in {"enable", "e"}:
                self._handle_enable(module, controller, notes, changes, errors)
                continue
            if command in {"disable", "d"}:
                self._handle_disable(module, controller, notes, changes)
                continue
            if command in {"test", "t"}:
                self._handle_test(module, notes, errors, changes)
                continue
            if command in {"show", "s"}:
                self._handle_show(module, notes, errors)
                continue
            print("INFO: commands are enable, disable, test, show, quit.")
            notes.append("INFO: unknown command.")

        self._emit_lines(module.status_lines(), notes)
        context.log_notes("notion_module", notes)
        if errors:
            context.log_errors(errors)
        if changes:
            context.log_changes(changes)
        preview = "\n".join(notes)
        return ActionResult(
            plan_text=plan_text,
            changes=changes,
            errors=errors,
            notes=notes,
            preview=preview,
        )

    # ------------------------------------------------------------------
    # Handlers

    def _handle_enable(
        self,
        module: NotionAccessModule,
        controller: Controller,
        notes: List[str],
        changes: List[str],
        errors: List[str],
    ) -> None:
        try:
            summary = module.enable_interactive()
        except ValueError as exc:
            message = f"ERROR: {exc}"
            print(message)
            errors.append(str(exc))
            notes.append(message)
            return
        controller.adapters["notion"] = NotionAdapter(controller.config.notion)
        message = f"INTERFACE: module enabled roots={summary['root_count']} source=notion_api_client"
        print(message)
        notes.append(message)
        changes.append("INTERFACE: Notion module enabled.")

    def _handle_disable(
        self,
        module: NotionAccessModule,
        controller: Controller,
        notes: List[str],
        changes: List[str],
    ) -> None:
        module.disable()
        controller.adapters["notion"] = NotionAdapter(controller.config.notion)
        message = "INTERFACE: module disabled"
        print(message)
        notes.append(message)
        changes.append("INTERFACE: Notion module disabled.")

    def _handle_test(
        self,
        module: NotionAccessModule,
        notes: List[str],
        errors: List[str],
        changes: List[str],
    ) -> None:
        report = module.test_connection()
        lines = self._format_report(report)
        self._emit_lines(lines, notes)
        if report.get("status") == "ok":
            changes.append("CONNECTIVITY: Notion connection verified.")
        else:
            detail = report.get("detail") or "connection failed"
            errors.append(str(detail))

    def _handle_show(
        self,
        module: NotionAccessModule,
        notes: List[str],
        errors: List[str],
    ) -> None:
        sample = module.show_data()
        lines = self._format_samples(sample)
        self._emit_lines(lines, notes)
        if sample.get("status") != "ok":
            detail = sample.get("detail") or "sample unavailable"
            errors.append(str(detail))

    # ------------------------------------------------------------------
    # Formatting helpers

    def _format_report(self, report: Dict[str, object]) -> List[str]:
        status = report.get("status", "unknown")
        user = report.get("integration_user") or "unknown"
        source = report.get("source") or "unknown"
        lines = [f"CONNECTIVITY: status={status} user={user} source={source}"]
        for root in report.get("roots", []):
            root_id = root.get("id", "?")
            root_status = root.get("status", "unknown")
            root_type = root.get("type", "?")
            objects = root.get("objects")
            has_more = root.get("has_more")
            detail = root.get("detail")
            summary = f"ROOT: id={root_id} status={root_status} type={root_type}"
            if objects is not None:
                summary += f" objects={objects}"
            if has_more:
                summary += " more=true"
            lines.append(summary)
            if detail:
                lines.append(f"DETAIL: {detail}")
        if report.get("timestamp"):
            lines.append(f"STAMP: {report['timestamp']}")
        if report.get("status") != "ok" and report.get("detail"):
            lines.append(f"ERROR: {report['detail']}")
        return lines

    def _format_samples(self, sample: Dict[str, object]) -> List[str]:
        source = sample.get("source", "unknown")
        lines = [
            f"SAMPLE: status={sample.get('status', 'unknown')} limit={sample.get('limit', '?')} source={source}"
        ]
        if sample.get("status") != "ok":
            detail = sample.get("detail")
            if detail:
                lines.append(f"ERROR: {detail}")
            return lines
        for entry in sample.get("samples", []):
            root_id = entry.get("id", "?")
            root_type = entry.get("type", "?")
            lines.append(f"ROOT: id={root_id} type={root_type}")
            if root_type == "database":
                for row in entry.get("rows", []):
                    rid = row.get("id", "?")
                    props = ",".join(row.get("properties", [])[:5])
                    lines.append(f"ROW: id={rid} fields={props}")
                if entry.get("status") == "error" and entry.get("detail"):
                    lines.append(f"ERROR: {entry['detail']}")
            if root_type == "page":
                for block in entry.get("blocks", []):
                    bid = block.get("id", "?")
                    btype = block.get("type", "?")
                    text = block.get("text", "")
                    lines.append(f"BLOCK: id={bid} type={btype} text={text[:60]}")
                if entry.get("status") == "error" and entry.get("detail"):
                    lines.append(f"ERROR: {entry['detail']}")
            if entry.get("has_more"):
                lines.append("MORE: true")
        if sample.get("timestamp"):
            lines.append(f"STAMP: {sample['timestamp']}")
        return lines

    def _emit_lines(self, lines: List[str], notes: List[str]) -> None:
        for line in lines:
            print(line)
            notes.append(line)

    def _require_module(self, controller: Controller) -> NotionAccessModule:
        module = controller.modules.get("notion_access")
        if not isinstance(module, NotionAccessModule):
            raise RuntimeError("Notion access module unavailable")
        return module
