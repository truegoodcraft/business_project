from __future__ import annotations
import os
from pathlib import Path


def resolve_db_path() -> str:
    """
    A canonical resolver for BUS_DB.
    - If BUS_DB is absolute -> use it.
    - If BUS_DB is relative (or unset) -> resolve relative to repo root.
    Repo root = two levels up from this file: .../TGC-BUS-Core/
    """
    raw = os.environ.get("BUS_DB", "data/app.db")
    p = Path(raw)
    if not p.is_absolute():
        repo_root = Path(__file__).resolve().parents[2]  # core/appdb/ -> core/ -> REPO
        p = (repo_root / raw).resolve()
    return str(p)


def _local_appdata() -> Path:
    # Fallback for non-Windows or missing env
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))


def app_root_dir() -> Path:
    """
    Root folder for BUS Core data.
    Default: %LOCALAPPDATA%/BUSCore
    Override: set BUSCORE_HOME to an absolute path (e.g., D:\\BUSCoreData).
    """
    custom = os.environ.get("BUSCORE_HOME")
    return Path(custom) if custom else (_local_appdata() / "BUSCore")


def app_dir() -> Path:
    """Return the canonical application data directory."""

    return app_root_dir() / "app"


def app_db_path() -> Path:
    return app_root_dir() / "app" / "app.db"


def ui_dir() -> Path:
    """
    Serve UI from the repo (core/ui). Do NOT point to AppData.
    """
    return Path(__file__).resolve().parents[2] / "core" / "ui"
