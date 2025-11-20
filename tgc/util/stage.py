# SPDX-License-Identifier: AGPL-3.0-or-later
"""Utilities for timing labeled stages of execution."""
import sys
import time
from typing import Optional


def stage(title: str) -> float:
    """Begin a stage with the given *title* and return the start timestamp."""
    sys.stdout.write(f"\n=== {title} ===\n")
    sys.stdout.flush()
    return time.perf_counter()


def stage_done(start: float, note: Optional[str] = "") -> None:
    """Log completion of a stage that started at *start* with an optional *note*."""
    elapsed = int((time.perf_counter() - start) * 1000)
    sys.stdout.write(f"\n--- done in {elapsed} ms {note}\n")
    sys.stdout.flush()

