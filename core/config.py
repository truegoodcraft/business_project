import json
from typing import Any, Dict
from core.appdb.paths import app_data_dir


def load_core_config() -> Dict[str, Any]:
    """
    Back-compat shim for test harnesses that import core.config.load_core_config.
    Reads a JSON config file if present; otherwise returns {}.
    """
    path = app_data_dir() / "core_config.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}
