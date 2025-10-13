from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.conn_broker import ClientHandle, ConnectionBroker


def test_no_escalation_rule():
    broker = ConnectionBroker(controller=None)

    def _issue_drive_client(scope):
        return ClientHandle(service="drive", scope=scope, handle=object(), metadata={})

    broker._issue_drive_client = _issue_drive_client  # type: ignore[attr-defined]

    base = broker.get_client("drive", "read_base")
    assert base is not None
    assert base.scope == "read_base"

    denied = broker.get_client("drive", "write")
    assert denied is None
