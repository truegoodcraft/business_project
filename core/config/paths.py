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
from sqlalchemy.engine import URL
from core.appdb.paths import app_db_path

if "LOCALAPPDATA" not in os.environ:
    os.environ["LOCALAPPDATA"] = str(Path.home() / "AppData" / "Local")

BUS_ROOT = Path(
    os.environ.get("BUS_ROOT") or (Path(os.environ["LOCALAPPDATA"]) / "BUSCore" / "app")
).resolve()
APP_DIR = BUS_ROOT
DATA_DIR = APP_DIR / "data"
JOURNALS_DIR = DATA_DIR / "journals"
IMPORTS_DIR = DATA_DIR / "imports"
for d in (DATA_DIR, JOURNALS_DIR, IMPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DB_PATH: Path = app_db_path()
# Build a Windows-safe URL; avoids backslash issues
DB_URL = URL.create(drivername="sqlite", database=str(DB_PATH))

DEV_UI_DIR = APP_DIR / "core" / "ui"
DEFAULT_UI_DIR = APP_DIR / "ui"

IS_DEV = bool(os.environ.get("BUS_ROOT"))

# Force repo UI in dev; keep previous default in prod
UI_DIR = DEV_UI_DIR if IS_DEV else DEFAULT_UI_DIR
UI_DIR.mkdir(parents=True, exist_ok=True)
