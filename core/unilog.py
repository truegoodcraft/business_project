"""Unified logging helpers."""

from __future__ import annotations

import json
import os
import pathlib
import time
from typing import Any

_DEFAULT_PATH = "reports/all.log"


def _log_path() -> pathlib.Path:
    path_value = os.getenv("UNIFIED_LOG_PATH", _DEFAULT_PATH)
    path = pathlib.Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(event: str, run_id: str | None = None, **fields: Any) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        "run_id": run_id,
        **fields,
    }
    with _log_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

