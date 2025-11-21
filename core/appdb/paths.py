# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

import os
from pathlib import Path


def _buscore_root() -> Path:
    p = Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_data_dir() -> Path:
    return _buscore_root()


def secrets_dir() -> Path:
    p = _buscore_root() / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_dir() -> Path:
    p = _buscore_root() / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_db_path() -> Path:
    """
    Canonical working DB path (Windows-only):
    %LOCALAPPDATA%\\BUSCore\\app\\app.db
    """

    root = Path(os.getenv("LOCALAPPDATA", "")) / "BUSCore" / "app"
    root.mkdir(parents=True, exist_ok=True)
    return root / "app.db"
