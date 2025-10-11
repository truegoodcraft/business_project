"""Run context and reporting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class RunContext:
    """State passed to actions during execution."""

    action_id: str
    apply: bool
    reports_root: Path
    metadata: Dict[str, str]

    run_id: str = field(init=False)
    run_dir: Path = field(init=False)
    plan_path: Path = field(init=False)
    changes_path: Path = field(init=False)
    errors_path: Path = field(init=False)

    def __post_init__(self) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{self.action_id}_{timestamp}"
        self.run_dir = self.reports_root / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.plan_path = self.run_dir / "plan.md"
        self.changes_path = self.run_dir / "changes.md"
        self.errors_path = self.run_dir / "errors.md"

    def log_plan(self, content: str) -> None:
        self._write_lines(self.plan_path, ["# Plan", "", content])

    def log_changes(self, lines: Iterable[str]) -> None:
        self._write_lines(self.changes_path, ["# Changes", ""] + list(lines))

    def log_errors(self, lines: Iterable[str]) -> None:
        self._write_lines(self.errors_path, ["# Errors", ""] + list(lines))

    def log_notes(self, title: str, lines: Iterable[str]) -> Path:
        target = self.run_dir / f"{title}.md"
        self._write_lines(target, [f"# {title}", ""] + list(lines))
        return target

    def _write_lines(self, path: Path, lines: List[str]) -> None:
        path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


@dataclass
class ActionResult:
    plan_text: str
    changes: List[str]
    errors: List[str]
    notes: Optional[List[str]] = None
    preview: Optional[str] = None

    def summary(self) -> str:
        output = ["Plan:\n" + self.plan_text]
        if self.preview:
            output.append(f"\nPreview:\n{self.preview}")
        if self.changes:
            output.append("\nChanges:")
            output.extend(f"  - {line}" for line in self.changes)
        if self.errors:
            output.append("\nErrors:")
            output.extend(f"  - {line}" for line in self.errors)
        if self.notes:
            output.append("\nNotes:")
            output.extend(f"  - {line}" for line in self.notes)
        return "\n".join(output)
