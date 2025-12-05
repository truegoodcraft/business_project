# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

__doc__ = r"Windows AppData design targets live under %LOCALAPPDATA%\BUSCore (DB default remains repo data/app.db unless BUS_DB is set)."

import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_db_path() -> str:
    """SoT resolver: repo-local data/app.db by default; BUS_DB when set."""

    raw = os.environ.get("BUS_DB")
    if raw:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (_repo_root() / raw).resolve()
        return str(candidate)
    return str((_repo_root() / "data" / "app.db").resolve())


def _localappdata() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    if value:
        return Path(value)
    # Non-Windows fallback for local dev shells
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


def app_db_design_target() -> Path:
    """Design target for the app database (not the default)."""

    return app_root() / "app.db"


def ensure_dirs() -> None:
    for path in (buscore_root(), app_root(), exports_dir(), secrets_dir(), state_dir()):
        path.mkdir(parents=True, exist_ok=True)
