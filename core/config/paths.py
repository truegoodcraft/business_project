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

from pathlib import Path

from sqlalchemy.engine import URL

from core.appdb.paths import app_db_path, app_root_dir, ui_dir

APP_ROOT: Path = app_root_dir()
APP_DIR: Path = APP_ROOT / "app"
STATE_DIR: Path = APP_DIR / "state"
DATA_DIR: Path = APP_DIR / "data"
JOURNALS_DIR: Path = DATA_DIR / "journals"
IMPORTS_DIR: Path = DATA_DIR / "imports"
DB_PATH: Path = app_db_path()
BUS_ROOT: Path = APP_ROOT
DB_URL = URL.create(drivername="sqlite+pysqlite", database=DB_PATH.as_posix())
UI_DIR: Path = ui_dir()
