from pathlib import Path
import os, json
from typing import Dict, Any, Tuple

_DEFAULT = {"tier": "community", "features": {}, "plugins": {}}


def _license_path() -> Path:
    # Dev: BUS_ROOT\license.json ; Prod: %LOCALAPPDATA%\BUSCore\license.json
    if os.environ.get("BUS_ROOT"):
        return Path(os.environ["BUS_ROOT"]) / "license.json"
    return Path(os.environ["LOCALAPPDATA"]) / "BUSCore" / "license.json"


def _read_json(path: Path) -> Tuple[Dict[str, Any], str | None]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else ({}, "not_a_dict")
    except FileNotFoundError:
        return {}, "not_found"
    except json.JSONDecodeError as e:
        return {}, f"json_error:{e.lineno}:{e.colno}"
    except Exception as e:
        return {}, f"error:{type(e).__name__}:{e}"


def get_license(*, force_reload: bool | None = None) -> Dict[str, Any]:
    # ALWAYS fresh in dev (BUS_ROOT set). No module-level cache.
    force_reload = True if os.environ.get("BUS_ROOT") else bool(force_reload)
    path = _license_path()
    raw, err = _read_json(path)
    data = {**_DEFAULT, **(raw if isinstance(raw, dict) else {})}
    if err and os.environ.get("BUS_ROOT"):
        data["_dev_error"] = err  # surfaced by /dev/license for debugging
    return data


def feature_enabled(name: str) -> bool:
    # CRITICAL: force fresh read so gates reflect current file
    lic = get_license(force_reload=True)
    val = lic.get("features", {}).get(name)
    if isinstance(val, bool):
        return val
    if isinstance(val, dict):
        flag = val.get("enabled")
        return bool(flag)
    return bool(val)
