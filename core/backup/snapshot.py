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

"""Backup helpers for snapshotting state before applying changes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
import zipfile

from core.unilog import write as uni_write


_SNAPSHOT_ROOT = Path("reports") / "snapshots"


def create_snapshot(run_id: str) -> Path | None:
    """Create a zip snapshot of the master index reports directory."""

    base_dir = Path("docs") / "master_index_reports"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = _SNAPSHOT_ROOT / f"{run_id}_{timestamp}.zip"
    _SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)

    if not base_dir.exists():
        # Nothing to snapshot yet; still emit an event for traceability.
        with zipfile.ZipFile(snapshot_path, "w", compression=zipfile.ZIP_DEFLATED):
            pass
        uni_write("backup.snapshot.created", run_id, path=str(snapshot_path), empty=True)
        return snapshot_path

    try:
        with zipfile.ZipFile(snapshot_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in base_dir.rglob("*"):
                if item.is_file():
                    archive.write(item, item.relative_to(base_dir.parent))
    except OSError as exc:
        logging.getLogger(__name__).warning("snapshot.failed", exc_info=exc)
        uni_write("backup.snapshot.error", run_id, error=str(exc))
        return None

    uni_write("backup.snapshot.created", run_id, path=str(snapshot_path), empty=False)
    return snapshot_path
