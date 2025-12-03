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

import json
from pathlib import Path

from sqlalchemy.engine import URL

from core.appdb.paths import app_db_path, app_root_dir, ui_dir, app_dir, resolve_db_path

APP_ROOT: Path = app_root_dir()
APP_DIR: Path = app_dir()
STATE_DIR: Path = APP_DIR / "state"
DATA_DIR: Path = APP_DIR / "data"
JOURNALS_DIR: Path = DATA_DIR / "journals"
IMPORTS_DIR: Path = DATA_DIR / "imports"
DB_PATH: Path = Path(resolve_db_path())
BUS_ROOT: Path = APP_ROOT
DB_URL = URL.create(drivername="sqlite+pysqlite", database=DB_PATH.as_posix())
UI_DIR: Path = ui_dir()

CONFIG_PATH = app_dir() / "config.json"


def _load_config_dict() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_config_dict(d: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_PATH.with_suffix(CONFIG_PATH.suffix + ".tmp")
    tmp_path.write_text(json.dumps(d, indent=2), encoding="utf-8")
    tmp_path.replace(CONFIG_PATH)
