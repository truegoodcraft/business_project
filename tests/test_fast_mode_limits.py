import types
from typing import Dict

import pytest

from core.bus.models import CommandContext
from tgc.master_index_controller import TraversalResult


class _FakeBroker:
    def get_client(self, service: str, scope: str = "read_base"):
        return types.SimpleNamespace(service=service, scope=scope, handle=object())


class _FakeMaster:
    def __init__(self, controller):
        self.controller = controller

    def _drive_module(self):
        return types.SimpleNamespace(
            config=types.SimpleNamespace(mime_whitelist=[], max_depth=0, page_size=200),
            root_ids=lambda: ["drive-root"],
        )

    def _drive_root_ids(self, module):
        return ["drive-root"]

    def _notion_module(self):
        return types.SimpleNamespace(config=types.SimpleNamespace(max_depth=0, page_size=10, root_ids=["notion-root"]))

    def _notion_root_ids(self, module):
        return ["notion-root"]


@pytest.mark.parametrize("service", ["drive", "notion"])
def test_fast_mode_limits(monkeypatch, service):
    limits: Dict[str, object] = {"fast": True, "max_files": 3, "max_pages": 2, "timeout_sec": 45, "page_size": 10}

    def fake_collect_drive_files(*args, **kwargs):
        return TraversalResult(
            records=[{"file_id": str(idx)} for idx in range(5)],
            errors=[],
            partial=False,
            reason=None,
        )

    def fake_collect_notion_pages(*args, **kwargs):
        return TraversalResult(
            records=[{"page_id": str(idx)} for idx in range(4)],
            errors=[],
            partial=False,
            reason=None,
        )

    outputs = []
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: outputs.append(" ".join(str(arg) for arg in args)))
    monkeypatch.setattr("plugins.discovery.drive.collect_drive_files", fake_collect_drive_files)
    monkeypatch.setattr("plugins.discovery.notion.collect_notion_pages", fake_collect_notion_pages)
    monkeypatch.setattr("plugins.discovery.drive.MasterIndexController", _FakeMaster)
    monkeypatch.setattr("plugins.discovery.notion.MasterIndexController", _FakeMaster)

    ctx = CommandContext(controller=object(), run_id="run", dry_run=False, limits=None, options={"discovery": {"limits": limits}}, logger=None)
    ctx.extras["conn_broker"] = _FakeBroker()

    if service == "drive":
        from plugins.discovery.drive import discover as drive_discover

        payload = drive_discover(ctx)
        assert payload["partial"] is True
        assert "fast" in (payload.get("reason") or "")
        assert any("Drive discovery" in line for line in outputs)
    else:
        from plugins.discovery.notion import discover as notion_discover

        payload = notion_discover(ctx)
        assert payload["partial"] is True
        assert "fast" in (payload.get("reason") or "")
        assert any("Notion discovery" in line for line in outputs)
