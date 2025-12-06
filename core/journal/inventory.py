# core/journal/inventory.py
import json
import logging
import os
from pathlib import Path
from typing import Dict

from core.config.paths import JOURNAL_DIR

logger = logging.getLogger(__name__)

INVENTORY_JOURNAL = Path(
    os.getenv("BUS_INVENTORY_JOURNAL", str(JOURNAL_DIR / "inventory.jsonl"))
)


def append_inventory(entry: Dict) -> None:
    """Append an inventory journal entry (best-effort, append-only)."""

    try:
        INVENTORY_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with open(INVENTORY_JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:  # pragma: no cover - best-effort logging
        logger.exception("Failed to append inventory journal at %s", INVENTORY_JOURNAL)


__all__ = ["INVENTORY_JOURNAL", "append_inventory"]
