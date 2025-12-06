# core/journal/manufacturing.py
import json
import logging
import os
from pathlib import Path
from typing import Dict

from core.config.paths import JOURNAL_DIR

logger = logging.getLogger(__name__)

MANUFACTURING_JOURNAL = Path(
    os.getenv("BUS_MANUFACTURING_JOURNAL", str(JOURNAL_DIR / "manufacturing.jsonl"))
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
