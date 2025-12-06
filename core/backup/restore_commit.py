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
import os
import random
import time
from pathlib import Path
import gc as _gc
import sqlite3 as _sqlite3
from typing import Callable, Optional, Tuple


def wal_checkpoint(db_path: Path) -> None:
    """Best-effort WAL checkpoint to flush -wal/-shm files before replace."""

    try:
        con = _sqlite3.connect(f"file:{db_path.as_posix()}?mode=rw", uri=True)
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            con.close()
    except Exception:
        # Non-fatal; preview already validated the DB.
        pass


def same_dir_temp(target_dir: Path, prefix: str) -> Path:
    """Allocate a temp file path in the same directory (and volume) as target."""

    target_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1000):
        p = target_dir / f"{prefix}.tmp.{int(time.time() * 1000)}.{i}"
        if not p.exists():
            return p
    raise RuntimeError("could_not_allocate_temp_path")


def close_all_db_handles(dispose_call: Optional[Callable[[], None]] = None) -> None:
    """
    Dispose SQLAlchemy pools AND force-close stray sqlite3 connections.
    Required on Windows to avoid WinError 32 during os.replace.
    """

    if dispose_call:
        try:
            dispose_call()
        except Exception:
            pass

    try:
        _gc.collect()
        for obj in list(_gc.get_objects()):
            try:
                if isinstance(obj, _sqlite3.Connection):
                    try:
                        obj.close()
                    except Exception:
                        pass
            except Exception:
                pass
        _gc.collect()
    except Exception:
        pass

    time.sleep(0.35)


def atomic_replace_with_retries(src: Path, dst: Path, retries: int = 30, backoff: float = 0.25) -> None:
    """
    Retry os.replace on Windows sharing violations with jittered backoff.
    """

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            os.replace(str(src), str(dst))
            return
        except OSError as exc:  # pragma: no cover - platform specific timing
            last_exc = exc
            winerr = getattr(exc, "winerror", 0)
            if winerr in (32, 33) or exc.errno in (errno.EACCES, errno.EBUSY):
                delay = min(backoff * (1.35 ** attempt) + random.uniform(0, 0.05), 2.0)
                time.sleep(delay)
                continue
            raise
    raise RuntimeError(
        f"replace_failed:{type(last_exc).__name__}:win32={getattr(last_exc, 'winerror', None)}:errno={getattr(last_exc, 'errno', None)}"
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


# Backwards compatibility for older imports
_wal_checkpoint = wal_checkpoint
_same_dir_temp = same_dir_temp

