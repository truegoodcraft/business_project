# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run context and reporting helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence


@dataclass
class RunContext:
    """State passed to actions during execution."""

    action_id: str
    apply: bool
    reports_root: Path
    metadata: Dict[str, str]
    options: Dict[str, object] = field(default_factory=dict)

    run_id: str = field(init=False)
    run_dir: Path = field(init=False)
    plan_path: Path = field(init=False)
    changes_path: Path = field(init=False)
    errors_path: Path = field(init=False)

    def __post_init__(self) -> None:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
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


def write_drive_files_markdown(output_dir: Path, rows: Sequence[Mapping[str, object]]) -> List[Path]:
    """Write Drive file metadata as Markdown table(s).

    The rows are sorted by ``modifiedTime`` descending and then ``name`` ascending.
    Large datasets are split into 5,000-row chunks to keep each Markdown file
    responsive. Chunked files are named ``drive_files_1.md``, ``drive_files_2.md``,
    and so on, while smaller datasets use ``drive_files.md``.
    """

    def _parse_modified(value: object) -> float:
        if isinstance(value, str) and value:
            text = value.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(text).timestamp()
            except (ValueError, OSError):
                return float("-inf")
        return float("-inf")

    def _stringify(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "yes" if value else ""
        if isinstance(value, (list, tuple, set)):
            parts = [str(item) for item in value if item not in (None, "")]
            return ", ".join(parts)
        if isinstance(value, Mapping):
            target = value.get("targetId") or value.get("id")
            return str(target) if target else ""
        return str(value)

    def _resolve_shortcut(row: Mapping[str, object]) -> str:
        shortcut = row.get("shortcut_target") or row.get("shortcutTargetId") or row.get("shortcut")
        if not shortcut:
            details = row.get("shortcut_details") or row.get("shortcutDetails")
            if isinstance(details, Mapping):
                shortcut = details.get("targetId") or details.get("id")
        if not shortcut:
            if row.get("is_shortcut"):
                return "yes"
            return ""
        return _stringify(shortcut)

    def _escape(value: str) -> str:
        return value.replace("|", r"\|").replace("\n", " ").strip()

    normalised: List[Dict[str, object]] = []
    for row in rows:
        if isinstance(row, Mapping):
            normalised.append(dict(row))
        else:  # pragma: no cover - defensive conversion
            try:
                normalised.append(dict(row))
            except Exception:
                continue

    sorted_rows = sorted(
        normalised,
        key=lambda item: (
            -_parse_modified(item.get("modifiedTime") or item.get("modified")),
            (str(item.get("name") or item.get("Name") or "").casefold()),
            str(item.get("name") or item.get("Name") or ""),
        ),
    )

    total = len(sorted_rows)
    chunk_size = 5_000
    output_dir.mkdir(parents=True, exist_ok=True)

    def _render_chunk(chunk_rows: Sequence[Mapping[str, object]]) -> str:
        lines = ["# Master Index — Drive Files", "", f"Total: {total}", ""]
        lines.append("| Name | Type | Size | Modified | ID | Shortcut | ParentIDs |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in chunk_rows:
            name = _escape(
                _stringify(row.get("name") or row.get("Name") or row.get("title"))
            )
            mime = _escape(_stringify(row.get("mimeType") or row.get("type")))
            size = _escape(_stringify(row.get("size")))
            modified = _escape(
                _stringify(row.get("modifiedTime") or row.get("modified"))
            )
            identifier = _escape(_stringify(row.get("id") or row.get("file_id")))
            shortcut = _escape(_resolve_shortcut(row))
            parents = _escape(
                _stringify(
                    row.get("parent_ids")
                    or row.get("parentIds")
                    or row.get("parentIDs")
                    or row.get("parents")
                )
            )
            lines.append(
                "| "
                + " | ".join([name, mime, size, modified, identifier, shortcut, parents])
                + " |"
            )
        return "\n".join(lines) + "\n"

    paths: List[Path] = []
    if total <= chunk_size:
        path = output_dir / "drive_files.md"
        path.write_text(_render_chunk(sorted_rows), encoding="utf-8")
        paths.append(path)
        return paths

    for index in range(0, total, chunk_size):
        chunk_rows = sorted_rows[index : index + chunk_size]
        chunk_index = index // chunk_size + 1
        path = output_dir / f"drive_files_{chunk_index}.md"
        path.write_text(_render_chunk(chunk_rows), encoding="utf-8")
        paths.append(path)
    return paths
