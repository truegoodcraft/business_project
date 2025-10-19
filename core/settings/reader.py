from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

READER_SETTINGS_PATH = Path("data/settings_reader.json")

_DEFAULT_SETTINGS: Dict[str, object] = {
    "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
    "local_roots": [],
}


def load_reader_settings() -> Dict[str, object]:
    if READER_SETTINGS_PATH.exists():
        try:
            return json.loads(READER_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_DEFAULT_SETTINGS)


def save_reader_settings(settings: Dict[str, object]) -> None:
    READER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    READER_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
