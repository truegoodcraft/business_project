"""Action base classes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..controller import Controller, ControllerAction, render_plan
from ..reporting import ActionResult, RunContext


@dataclass
class SimpleAction(ControllerAction):
    """Action template that uses callbacks for plan and run."""

    def build_plan(self, controller: Controller) -> str:
        raise NotImplementedError

    def run(self, controller: Controller, context: RunContext) -> ActionResult:
        raise NotImplementedError

    def _dry_run_message(self) -> List[str]:
        return ["Dry-run: no changes applied."]

    def render_plan(self, title: str, steps: List[str], warnings: List[str] | None = None, notes: List[str] | None = None) -> str:
        return render_plan(title, steps, warnings, notes)
