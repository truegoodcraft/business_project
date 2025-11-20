# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.conn_broker import ClientHandle, ConnectionBroker


def test_no_escalation_rule():
    broker = ConnectionBroker(controller=None)

    def _drive_provider(scope: str) -> ClientHandle:
        return ClientHandle(service="drive", scope=scope, handle=object(), metadata={})

    broker.register(
        "drive",
        provider=_drive_provider,
        probe=lambda handle: {"ok": handle is not None, "scope": getattr(handle, "scope", None)},
    )

    base = broker.get_client("drive", "read_base")
    assert base is not None
    assert base.scope == "read_base"

    denied = broker.get_client("drive", "write")
    assert denied is None
