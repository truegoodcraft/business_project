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

"""Detect residual legacy branding references."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List, Tuple

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


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    for part in rel.parts:
        if part in EXCLUDED_DIR_PARTS:
            return True
    for prefix in EXCLUDED_PREFIXES:
        if rel.parts[: len(prefix.parts)] == prefix.parts:
            return True
    return False


def _iter_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if path.is_file() and not _is_excluded(path) and path.suffix.lower() in TARGET_EXTENSIONS:
            yield path


def _find_offenders(path: Path) -> List[Tuple[int, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    offenders: List[Tuple[int, str]] = []
    lines = content.splitlines()
    for match in LEGACY_PATTERN.finditer(content):
        line_no = content.count("\n", 0, match.start()) + 1
        line = lines[line_no - 1] if line_no - 1 < len(lines) else ""
        offenders.append((line_no, line.strip()))
    return offenders


def main() -> int:
    offenders: List[Tuple[Path, int, str]] = []
    for path in _iter_files():
        matches = _find_offenders(path)
        for line_no, snippet in matches:
            offenders.append((path.relative_to(ROOT), line_no, snippet))
            if len(offenders) >= 20:
                break
        if len(offenders) >= 20:
            break
    if offenders:
        print("Legacy branding references detected:")
        for rel_path, line_no, snippet in offenders:
            print(f"- {rel_path}:L{line_no}: {snippet}")
        return 2
    print("Branding check passed. No legacy references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
