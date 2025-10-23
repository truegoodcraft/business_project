"""Utilities for discovering allowed local reader roots."""

from __future__ import annotations

import json
import os
import pathlib
from typing import List


def get_allowed_local_roots() -> List[str]:
    """Return list of allowed local roots.

    Attempts to use existing settings helpers when available. Falls back to
    BUSCore configuration files under ``%LOCALAPPDATA%``.
    """

    try:
        from core.settings.reader import (  # type: ignore
            get_allowed_local_roots as settings_roots,
        )

        return settings_roots()
    except Exception:  # pragma: no cover - defensive import guard
        pass

    try:
        from core.settings.reader_store import (  # type: ignore
            get_allowed_local_roots as settings_roots,
        )

        return settings_roots()
    except Exception:  # pragma: no cover - defensive import guard
        pass

    cfg_dir = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
    for name in ("reader.json", "settings_reader.json", "settings.json"):
        path = cfg_dir / name
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # pragma: no cover - best effort load
                continue
            roots = (
                data.get("local_roots")
                or data.get("roots")
                or data.get("allowed_roots")
            )
            if isinstance(roots, list):
                return roots
    return []
