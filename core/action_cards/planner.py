# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Planner helpers that translate findings into action cards."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from uuid import uuid4

from .model import ActionCard


def _coerce_mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "__dict__"):
        return {**asdict(value)} if hasattr(value, "__dataclass_fields__") else vars(value)
    return {}


def _extract_records(finding: Mapping[str, Any]) -> List[Dict[str, Any]]:
    records = finding.get("records")
    if isinstance(records, list):
        normalised: List[Dict[str, Any]] = []
        for item in records:
            if isinstance(item, Mapping):
                normalised.append(dict(item))
            else:
                try:
                    normalised.append(dict(item))
                except Exception:  # pragma: no cover - defensive
                    continue
        return normalised
    return []


def _extract_errors(finding: Mapping[str, Any]) -> List[str]:
    errors = finding.get("errors")
    if isinstance(errors, Iterable) and not isinstance(errors, (str, bytes)):
        return [str(item) for item in errors if item]
    return []


def build_cards_from_findings(findings: Mapping[str, Any]) -> List[ActionCard]:
    """Produce action cards from discovery findings."""

    notion = _coerce_mapping(findings.get("discovery.notion"))
    drive = _coerce_mapping(findings.get("discovery.drive"))
    sheets = _coerce_mapping(findings.get("discovery.sheets"))

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path("docs") / "master_index_reports" / f"master_index_{timestamp}"

    notion_records = _extract_records(notion)
    drive_records = _extract_records(drive)
    sheets_rows = _extract_records(sheets)

    summary = (
        f"Plan to write Master Index Markdown (Notion={len(notion_records)}, "
        f"Drive={len(drive_records)}, Sheets tabs={len(sheets_rows)})"
    )

    card = ActionCard(
        id=str(uuid4()),
        kind="index.markdown",
        title="Write Master Index Markdown",
        summary=summary,
        proposed_by_plugin="writer.markdown",
        data={
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "output_dir": str(output_dir),
            "notion": {
                "records": notion_records,
                "errors": _extract_errors(notion),
                "roots": list(notion.get("roots", [])),
                "elapsed": notion.get("elapsed"),
                "message": notion.get("message"),
                "partial": bool(notion.get("partial")),
                "reason": notion.get("reason"),
            },
            "drive": {
                "records": drive_records,
                "errors": _extract_errors(drive),
                "roots": list(drive.get("roots", [])),
                "elapsed": drive.get("elapsed"),
                "message": drive.get("message"),
                "partial": bool(drive.get("partial")),
                "reason": drive.get("reason"),
            },
            "sheets": {
                "records": sheets_rows,
                "errors": _extract_errors(sheets),
                "roots": list(sheets.get("roots", [])),
                "elapsed": sheets.get("elapsed"),
                "message": sheets.get("message"),
                "partial": bool(sheets.get("partial")),
                "reason": sheets.get("reason"),
            },
        },
        diff=[],
        risk="low",
        prerequisites=[],
    )

    return [card]
