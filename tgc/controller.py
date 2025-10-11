"""Core controller for orchestrating workflow actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .config import AppConfig
from .organization import OrganizationProfile, organization_status_lines
from .reporting import ActionResult, RunContext


@dataclass
class ControllerAction:
    """Metadata describing a runnable controller action."""

    id: str
    name: str
    description: str

    def build_plan(self, controller: "Controller") -> str:
        raise NotImplementedError

    def run(self, controller: "Controller", context: RunContext) -> ActionResult:
        raise NotImplementedError


@dataclass
class Controller:
    config: AppConfig
    adapters: Dict[str, object]
    organization: OrganizationProfile
    reports_root: Path = Path("reports")
    actions: Dict[str, ControllerAction] = field(default_factory=dict)

    def register_action(self, action: ControllerAction) -> None:
        if action.id in self.actions:
            raise ValueError(f"Action '{action.id}' already registered")
        self.actions[action.id] = action

    def available_actions(self) -> List[ControllerAction]:
        return [self.actions[key] for key in sorted(self.actions)]

    def get_action(self, action_id: str) -> ControllerAction:
        try:
            return self.actions[action_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Unknown action '{action_id}'") from exc

    def build_plan(self, action_id: str) -> str:
        action = self.get_action(action_id)
        return action.build_plan(self)

    def run_action(self, action_id: str, apply: bool) -> ActionResult:
        action = self.get_action(action_id)
        plan_text = action.build_plan(self)
        context = RunContext(
            action_id=action_id,
            apply=apply,
            reports_root=self.reports_root,
            metadata={"action_name": action.name, "apply": str(apply)},
        )
        context.log_plan(plan_text)
        result = action.run(self, context)
        if result.changes:
            context.log_changes(result.changes)
        if result.errors:
            context.log_errors(result.errors)
        if result.notes:
            context.log_notes("notes", result.notes)
        return ActionResult(
            plan_text=plan_text,
            changes=result.changes,
            errors=result.errors,
            notes=result.notes,
            preview=result.preview,
        )

    def mask_config(self) -> Dict[str, Optional[str]]:
        return self.config.mask_sensitive()

    def adapter_status(self) -> Dict[str, bool]:
        return self.config.enabled_modules()

    def adapter_status_report(self) -> List[Dict[str, Any]]:
        """Return detailed status information for each registered adapter."""

        report: List[Dict[str, Any]] = []
        for key in sorted(self.adapters):
            adapter = self.adapters[key]
            status = adapter.status_report()
            status["key"] = key
            report.append(status)
        return report

    def organization_summary(self) -> List[str]:
        return list(organization_status_lines(self.organization))

    def list_reports(self) -> List[Path]:
        if not self.reports_root.exists():
            return []
        return sorted([path for path in self.reports_root.iterdir() if path.is_dir()])

    def adapters_for(self, *keys: str) -> Dict[str, object]:
        return {key: self.adapters.get(key) for key in keys if key in self.adapters}

    def configured_adapters(self, *keys: str) -> Dict[str, object]:
        return {key: adapter for key, adapter in self.adapters_for(*keys).items() if getattr(adapter, "is_configured", lambda: False)()}


def render_plan(title: str, steps: Iterable[str], warnings: Optional[Iterable[str]] = None, notes: Optional[Iterable[str]] = None) -> str:
    lines: List[str] = [f"# {title}", ""]
    lines.append("## Steps")
    lines.extend(f"- {step}" for step in steps)
    if warnings:
        lines.append("\n## Warnings")
        lines.extend(f"- {warning}" for warning in warnings)
    if notes:
        lines.append("\n## Notes")
        lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines)
