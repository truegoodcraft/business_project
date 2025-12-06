# SPDX-License-Identifier: AGPL-3.0-or-later
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

"""Helpers for robust restore commit on Windows (atomic replace + journaling)."""

from __future__ import annotations

import errno
import gc
import os
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional, Tuple


def _wal_checkpoint(db_path: Path) -> None:
    """Best-effort WAL checkpoint to flush -wal/-shm files before replace."""

    try:
        con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=rw", uri=True)
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            con.close()
    except Exception:
        # Non-fatal; preview already validated the DB.
        pass


def _same_dir_temp(target_dir: Path, prefix: str) -> Path:
    """Allocate a temp file path in the same directory (and volume) as target."""

    target_dir.mkdir(parents=True, exist_ok=True)
    for i in range(100):
        p = target_dir / f"{prefix}.tmp.{int(time.time() * 1000)}.{i}"
        if not p.exists():
            return p
    raise RuntimeError("could_not_allocate_temp_path")


def close_all_db_handles(dispose_call: Optional[Callable[[], None]] = None) -> None:
    """Dispose SQLAlchemy engine/pool and encourage GC to release handles."""

    if dispose_call:
        try:
            dispose_call()
        except Exception:
            pass
    gc.collect()
    time.sleep(0.1)


def atomic_replace_with_retries(src: Path, dst: Path, retries: int = 10, backoff: float = 0.2) -> None:
    """Atomic replace with backoff for Windows sharing violations."""

    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            os.replace(str(src), str(dst))
            return
        except OSError as exc:  # pragma: no cover - platform specific timing
            last_exc = exc
            winerr = getattr(exc, "winerror", 0)
            if winerr in (32, 33) or exc.errno in (errno.EACCES, errno.EBUSY):
                time.sleep(backoff)
                continue
            raise
    raise RuntimeError(
        f"replace_failed:{type(last_exc).__name__}:{getattr(last_exc, 'winerror', None)}:"
        f"{getattr(last_exc, 'errno', None)}"
    )


def archive_journals(journal_dir: Path, ts: str) -> Tuple[int, int]:
    """Archive existing journals and recreate empty inventory/manufacturing logs."""

    archived = 0
    errors = 0
    if not journal_dir.exists():
        return (0, 0)

    for p in journal_dir.glob("*.jsonl"):
        try:
            new_name = p.with_suffix(p.suffix + f".pre-restore-{ts}")
            p.replace(new_name)
            archived += 1
        except Exception:
            errors += 1

    try:
        (journal_dir / "inventory.jsonl").touch(exist_ok=True)
        (journal_dir / "manufacturing.jsonl").touch(exist_ok=True)
    except Exception:
        pass

    return (archived, errors)

