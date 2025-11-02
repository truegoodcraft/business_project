from pathlib import Path
import os
import json
from typing import Dict, Any

# --- PATH: BUS_ROOT = dev, AppData = prod ---
def _license_path() -> Path:
    if os.environ.get("BUS_ROOT"):
        return Path(os.environ["BUS_ROOT"]) / "license.json"
    else:
        return Path(os.environ["LOCALAPPDATA"]) / "BUSCore" / "license.json"

# --- LOAD: Fresh every call in dev ---
def get_license(*, force_reload: bool | None = None) -> Dict[str, Any]:
    if force_reload is None:
        force_reload = bool(os.environ.get("BUS_ROOT"))
    
    path = _license_path()
    data = {"tier": "community", "features": {}, "plugins": {}}
    
    if not force_reload and hasattr(get_license, "_cached"):
        return get_license._cached  # Prod cache
    
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        raw = {}
    
    # Normalize
    data.update(raw)
    data.setdefault("tier", "community")
    data.setdefault("features", {})
    data.setdefault("plugins", {})
    
    if force_reload:
        return data
    else:
        get_license._cached = data
        return data

# --- FEATURE CHECK: Always fresh in dev ---
def feature_enabled(name: str) -> bool:
    lic = get_license()  # Reloads every call when BUS_ROOT set
    return bool(lic.get("features", {}).get(name, False))
