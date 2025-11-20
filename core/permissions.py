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
import pathlib

_STORE = pathlib.Path("consents.json")
_CONSENTS = json.loads(_STORE.read_text()) if _STORE.exists() else {}


def approved(plugin: str, scope: str) -> bool:
    return _CONSENTS.get(f"{plugin}:{scope}", False)


def require(plugin: str, scopes: list[str]):
    missing = [s for s in scopes if not approved(plugin, s)]
    if missing:
        raise PermissionError(f"Missing consent: {plugin} -> {', '.join(missing)}")


def grant(plugin: str, scopes: list[str]):
    for s in scopes:
        _CONSENTS[f"{plugin}:{s}"] = True
    _STORE.write_text(json.dumps(_CONSENTS, indent=2))
