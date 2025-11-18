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
import pathlib


def _buscore_root() -> pathlib.Path:
    p = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_data_dir() -> pathlib.Path:
    return _buscore_root()


def secrets_dir() -> pathlib.Path:
    p = _buscore_root() / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_dir() -> pathlib.Path:
    p = _buscore_root() / "state"
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_db_path() -> pathlib.Path:
    return app_data_dir() / "app.db"
