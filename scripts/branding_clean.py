#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dry-run friendly branding cleanup utility."""

from __future__ import annotations

import argparse
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
TARGET_EXTENSIONS = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".ini", ".txt", ".ps1"}
EXCLUDED_DIR_PARTS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
}
EXCLUDED_PREFIXES = [Path("docs/master_index_reports"), Path("reports/branding")]
LEGACY_PATTERN = re.compile(r"(?i)true\s*[-_\s]*good\s*[-_\s]*craft")
VENDOR_KEYWORDS = {
    "built by",
    "made by",
    "publisher",
    "author",
    "maintained by",
    "maker",
    "vendor",
}


@dataclass
class Replacement:
    path: Path
    new_content: str
    lines: Dict[int, Dict[str, object]]
    replacements: int


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    for part in rel.parts:
        if part in EXCLUDED_DIR_PARTS:
            return True
    for prefix in EXCLUDED_PREFIXES:
        if rel.parts[: len(prefix.parts)] == prefix.parts:
            return True
    return False


def _adjust_case(template: str, replacement: str) -> str:
    if template.isupper():
        return replacement.upper()
    if template.islower():
        return replacement.lower()
    return replacement


def _choose_replacement(full_text: str, start: int, end: int, match_text: str) -> Optional[str]:
    before = full_text[max(0, start - 50) : start].lower()
    after = full_text[end : end + 50].lower()
    if "://" in before or "@" in before or "@" in after:
        return None
    if any(keyword in before for keyword in VENDOR_KEYWORDS):
        return _adjust_case(match_text, "TGC Systems")
    return _adjust_case(match_text, "TGC Frame")


def _scan_file(path: Path) -> Optional[Replacement]:
    if _is_excluded(path):
        return None
    if path.suffix.lower() not in TARGET_EXTENSIONS:
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    matches: List[tuple[int, str, str]] = []

    def _sub(match: re.Match[str]) -> str:
        replacement = _choose_replacement(content, match.start(), match.end(), match.group(0))
        if replacement is None or replacement == match.group(0):
            return match.group(0)
        matches.append((match.start(), match.group(0), replacement))
        return replacement

    new_content = LEGACY_PATTERN.sub(_sub, content)
    if not matches:
        return None

    original_lines = content.splitlines()
    updated_lines = new_content.splitlines()
    line_map: Dict[int, Dict[str, object]] = {}
    for start, original, replacement in matches:
        line_no = content.count("\n", 0, start) + 1
        before_line = original_lines[line_no - 1] if line_no - 1 < len(original_lines) else ""
        after_line = updated_lines[line_no - 1] if line_no - 1 < len(updated_lines) else ""
        entry = line_map.setdefault(
            line_no,
            {"before": before_line.strip(), "after": after_line.strip(), "count": 0},
        )
        entry["count"] = int(entry["count"]) + 1
    total_replacements = sum(int(data["count"]) for data in line_map.values())
    return Replacement(path=path, new_content=new_content, lines=line_map, replacements=total_replacements)


def _iter_target_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if path.is_file():
            yield path


def _write_report(report_path: Path, rows: Sequence[tuple[str, int, str, str]]) -> None:
    lines = ["# Branding Clean Report", ""]
    lines.append("| File | Lines Changed | Before (snippet) | After (snippet) |")
    lines.append("| --- | --- | --- | --- |")
    if rows:
        for file_path, count, before, after in rows:
            lines.append(f"| {file_path} | {count} | {before} | {after} |")
    else:
        lines.append("| _None_ | 0 | — | — |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize legacy branding references.")
    parser.add_argument("--apply", action="store_true", help="Apply branding replacements in place")
    args = parser.parse_args(argv)

    replacements: List[Replacement] = []
    for path in _iter_target_files():
        result = _scan_file(path)
        if result is not None:
            replacements.append(result)

    replacements.sort(key=lambda item: str(item.path.relative_to(ROOT)))

    timestamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_dir = ROOT / "reports" / "branding"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"branding_report_{timestamp}.md"

    report_rows: List[tuple[str, int, str, str]] = []
    total_replacements = 0

    for result in replacements:
        rel_path = result.path.relative_to(ROOT)
        if args.apply:
            result.path.write_text(result.new_content, encoding="utf-8")
        total_replacements += result.replacements
        before_snippets: List[str] = []
        after_snippets: List[str] = []
        for line_no in sorted(result.lines):
            data = result.lines[line_no]
            before_snippets.append(f"L{line_no}: {data['before']}")
            after_snippets.append(f"L{line_no}: {data['after']}")
        report_rows.append(
            (
                str(rel_path),
                len(result.lines),
                "<br>".join(before_snippets),
                "<br>".join(after_snippets),
            )
        )

    _write_report(report_path, report_rows)

    if args.apply:
        print("Branding apply complete.")
        print(f"Files updated: {len(report_rows)}")
    else:
        print("Branding dry-run complete.")
        print(f"Files to change: {len(report_rows)}")
    print(f"Total replacements: {total_replacements}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
