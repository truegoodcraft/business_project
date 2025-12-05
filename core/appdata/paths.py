# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
import os

__doc__ = r"""
Windows AppData conventions (SoT):
  Base: %LOCALAPPDATA%\BUSCore
  DB default (Windows): %LOCALAPPDATA%\BUSCore\app\app.db
  On non-Windows dev shells, use ~/.buscore/app/app.db
"""


def _is_windows() -> bool:
    return os.name == "nt"


def _localappdata() -> Path:
    lad = os.environ.get("LOCALAPPDATA")
    if lad:
        return Path(lad)
    # Fallback (non-Windows dev shells)
    return Path.home() / ".buscore"


def buscore_root() -> Path:
    return _localappdata() / "BUSCore"


def app_root() -> Path:
    return buscore_root() / "app"


def config_path() -> Path:
    return buscore_root() / "config.json"


def license_path() -> Path:
    return buscore_root() / "license.json"


def reader_settings_path() -> Path:
    return buscore_root() / "settings_reader.json"


def exports_dir() -> Path:
    return buscore_root() / "exports"


def secrets_dir() -> Path:
    return buscore_root() / "secrets"


def state_dir() -> Path:
    return buscore_root() / "state"


def app_db_default() -> Path:
    if _is_windows():
        return app_root() / "app.db"
    # non-Windows dev fallback target
    return Path.home() / ".buscore" / "app" / "app.db"


def app_db_design_target() -> Path:
    # Alias for clarity when other modules want the design-target location
    return app_db_default()


def ensure_roots() -> None:
    for p in (buscore_root(), app_root(), exports_dir(), secrets_dir(), state_dir()):
        p.mkdir(parents=True, exist_ok=True)


def resolve_db_path() -> str:
    """
    New SoT (Windows): default DB lives in %LOCALAPPDATA%\BUSCore\app\app.db
    If BUS_DB is set, use it exactly.
    On non-Windows dev shells, fallback to ~/.buscore/app/app.db as default.
    """
    env_db = os.environ.get("BUS_DB")
    if env_db:
        return str(Path(env_db).resolve())
    ensure_roots()
    return str(app_db_default().resolve())


# Legacy repo path helper (for one-time migration only)
def legacy_repo_db() -> Path:
    return (Path.cwd() / "data" / "app.db").resolve()
