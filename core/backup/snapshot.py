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
