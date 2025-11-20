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

from core.config_validate import validate_plugin_config
from core.unilog import write as uni_write


def system_check() -> None:
    plugins = ["notion-plugin", "google-plugin"]
    issues: list[str] = []
    for pl in plugins:
        issues.extend(validate_plugin_config(pl))
    if issues:
        print("\nSystem Check — MISSING\n" + "\n".join(f" - {x}" for x in issues))
    else:
        print("\nSystem Check — READY ✅")
    uni_write("system_check", None, status=("READY" if not issues else "MISSING"), issues=issues)
