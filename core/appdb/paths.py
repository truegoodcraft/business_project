from __future__ import annotations
import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "TGC-BUS-Core"
APP_AUTHOR = "TrueGoodCraft"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _appdata_root() -> Path:
    root = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_db_path() -> str:
    """
    Resolve the database path honoring BUS_DB when set; otherwise default to
    an AppData location (platformdirs user_data_dir).
    - BUS_DB absolute: use as-is
    - BUS_DB relative: resolve relative to repo root for backwards compatibility
    - Unset: %LOCALAPPDATA%/TrueGoodCraft/TGC-BUS-Core/app.db (created if missing)
    """

    raw = os.environ.get("BUS_DB")
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = (_repo_root() / raw).resolve()
        return str(p)

    return str(app_db_path())


def app_root_dir() -> Path:
    """Root folder for BUS Core data (AppData by default)."""

    custom = os.environ.get("BUSCORE_HOME")
    root = Path(custom) if custom else _appdata_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def app_dir() -> Path:
    """Return the canonical application data directory."""

    target = app_root_dir() / "app"
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_db_path() -> Path:
    path = app_dir() / "app.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ui_dir() -> Path:
    """
    Serve UI from the repo (core/ui). Do NOT point to AppData.
    """
    return Path(__file__).resolve().parents[2] / "core" / "ui"
