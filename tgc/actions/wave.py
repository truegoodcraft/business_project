"""Optional Wave action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller
from ..reporting import ActionResult, RunContext
from .base import SimpleAction


@dataclass
class WaveAction(SimpleAction):
    id: str = "9"
    name: str = "Wave"
    description: str = "Discover Wave data and plan exports"

    def build_plan(self, controller: Controller) -> str:
        steps = [
            "Check Wave adapter configuration",
            "Fetch recent financial data (simulated)",
            "Prepare export plan",
        ]
        warnings: List[str] = []
        wave = controller.adapters.get("wave")
        if not wave or not getattr(wave, "is_configured", lambda: False)():
            warnings.append("Wave adapter not configured; will skip discovery.")
        return self.render_plan(self.name, steps, warnings=warnings)

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        wave = controller.adapters.get("wave")
        plan_text = controller.build_plan(self.id)
        if not wave or not getattr(wave, "is_configured", lambda: False)():
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=["Wave adapter not configured."],
                notes=self._dry_run_message(),
            )
        discovery = getattr(wave, "discover_financials", lambda: ["Wave discovery not implemented."])()
        context.log_notes("wave_discovery", discovery)
        if not context.apply:
            return ActionResult(
                plan_text=plan_text,
                changes=[],
                errors=[],
                notes=self._dry_run_message(),
                preview="\n".join(discovery),
            )
        return ActionResult(
            plan_text=plan_text,
            changes=discovery,
            errors=[],
            notes=["Wave discovery complete (simulated)."],
        )
