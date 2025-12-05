# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized BUSCore AppData path helpers.

This module defines the SoT-correct runtime locations under
``%LOCALAPPDATA%\BUSCore`` (or a developer-friendly fallback when that
environment variable is absent). The database design target is exposed but not
enabled by default; the running default remains the repo-local
``data/app.db`` unless ``BUS_DB`` is set.
"""

from __future__ import annotations

import os
from pathlib import Path


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
