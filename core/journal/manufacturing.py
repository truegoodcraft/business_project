# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

# core/journal/manufacturing.py
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

def _journals_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        # Linux/macOS fallback
        root = os.path.expanduser("~/.local/share")
    d = Path(root) / "BUSCore" / "app" / "data" / "journals"
    d.mkdir(parents=True, exist_ok=True)
    return d


MANUFACTURING_JOURNAL = Path(
    os.getenv("BUS_MANUFACTURING_JOURNAL", str(_journals_dir() / "manufacturing.jsonl"))
)


def append_mfg_journal(entry: Dict) -> None:
    """Append a manufacturing journal entry (best-effort, append-only)."""

    try:
        MANUFACTURING_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with open(MANUFACTURING_JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:  # pragma: no cover - best-effort logging
        logger.exception(
            "Failed to append manufacturing journal at %s", MANUFACTURING_JOURNAL
        )


__all__ = ["MANUFACTURING_JOURNAL", "append_mfg_journal"]
