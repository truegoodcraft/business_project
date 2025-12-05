from __future__ import annotations
import os
from pathlib import Path

from core.appdata import paths as appdata_paths


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_db_path() -> str:
    """
    Resolve the database path honoring BUS_DB when set; otherwise default to
    the repo-local data/app.db (SoT gotcha).
    - BUS_DB absolute: use as-is
    - BUS_DB relative: resolve relative to repo root for backwards compatibility
    - Unset: repo/data/app.db
    """

    raw = os.environ.get("BUS_DB")
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = (_repo_root() / raw).resolve()
        return str(p)

    return str((_repo_root() / "data" / "app.db").resolve())


def app_root_dir() -> Path:
    """Root folder for BUS Core runtime data (AppData design target)."""

    root = appdata_paths.buscore_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def app_dir() -> Path:
    """Return the canonical application data directory (AppData design target)."""

    target = appdata_paths.app_root()
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_db_path() -> Path:
    """Design-target database path (not the running default)."""

    path = appdata_paths.app_db_design_target()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ui_dir() -> Path:
    """Serve UI from the repo (core/ui). Do NOT point to AppData."""

    return Path(__file__).resolve().parents[2] / "core" / "ui"
