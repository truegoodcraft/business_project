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

import json, time, pathlib

from core.unilog import write as uni_write

LOG = pathlib.Path("reports/audit.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


def write_audit(
    run_id: str,
    plugin: str,
    capability: str,
    scopes: list[str],
    outcome: str,
    ms: int,
    notes: str = "",
) -> None:
    LOG.write_text("", append=True) if not LOG.exists() else None
    with LOG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "run_id": run_id,
                    "plugin": plugin,
                    "capability": capability,
                    "scopes": scopes,
                    "outcome": outcome,
                    "ms": ms,
                    "notes": notes,
                }
            )
            + "\n"
        )
    uni_write(
        "audit.entry",
        run_id,
        plugin=plugin,
        capability=capability,
        scopes=scopes,
        outcome=outcome,
        ms=ms,
        notes=notes,
    )
