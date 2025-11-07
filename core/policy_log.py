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
import time
import pathlib
import hashlib

from core.unilog import write as uni_write


LOG = pathlib.Path("reports/policy.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


def log_policy(raw_text: str, decision: dict) -> None:
    user_hash = hashlib.sha256(raw_text.encode()).hexdigest()[:16]
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_hash": user_hash,
        "decision": decision,
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    uni_write("policy.decision", decision.get("run_id"), user_hash=user_hash, decision=decision)
