from pathlib import Path
import os, json
from typing import Dict, Any

def _license_path() -> Path:
    # Dev: BUS_ROOT; Prod: AppData
    if os.environ.get("BUS_ROOT"):
        return Path(os.environ["BUS_ROOT"]) / "license.json"
    return Path(os.environ["LOCALAPPDATA"]) / "BUSCore" / "license.json"

def get_license(*, force_reload: bool | None = None) -> Dict[str, Any]:
    # No cache in dev. Always reload when BUS_ROOT is set.
    force_reload = True if os.environ.get("BUS_ROOT") else bool(force_reload)
    path = _license_path()
    data: Dict[str, Any] = {"tier": "community", "features": {}, "plugins": {}}
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
            if isinstance(raw, dict):
                data.update(raw)
    except Exception:
        pass
    return data

def feature_enabled(name: str) -> bool:
    # Force fresh read so gates reflect current license file
    lic = get_license(force_reload=True)
    return bool(lic.get("features", {}).get(name, False))
