import json
import os
import pathlib
from typing import Any, Dict, List

_CFG_DIR = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
_CFG_DIR.mkdir(parents=True, exist_ok=True)
_CFG_FILE = _CFG_DIR / "settings_reader.json"

_STATE: Dict[str, Any] = {
    "enabled": {"drive": True, "local": True, "notion": False, "smb": False},
    "local_roots": [],
    "drive_includes": {
        "include_my_drive": False,
        "my_drive_root_id": "",
        "include_shared_drives": False,
    },
}


def _load_file() -> Dict[str, Any]:
    if _CFG_FILE.exists():
        try:
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_STATE)


def load_settings() -> Dict[str, Any]:
    global _STATE
    _STATE = _load_file()
    return dict(_STATE)


def save_settings(s: Dict[str, Any]) -> None:
    global _STATE
    _STATE = dict(_STATE | s)
    _CFG_FILE.write_text(json.dumps(_STATE, indent=2), encoding="utf-8")


def get_allowed_local_roots() -> List[str]:
    return list(_STATE.get("local_roots", []))


def set_allowed_local_roots(roots: List[str]) -> None:
    s = dict(_STATE)
    s["local_roots"] = list(roots or [])
    save_settings(s)


# Initialize at import
load_settings()
