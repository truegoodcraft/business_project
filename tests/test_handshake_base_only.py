import types
from typing import Dict, List

import pytest

from core.bus.models import CommandContext
from tgc.cli_main import cmd_go


@pytest.fixture(autouse=True)
def _silence_stage(monkeypatch):
    monkeypatch.setattr("tgc.cli_main.stage", lambda title: 0.0)
    monkeypatch.setattr("tgc.cli_main.stage_done", lambda start: None)


class _StubController:
    def __init__(self) -> None:
        self.modules: Dict[str, object] = {}
        self.adapters: Dict[str, object] = {}


def test_handshake_base_only(monkeypatch):
    outputs: List[str] = []
    responses = iter(["s"])  # skip discovery after handshake

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        try:
            return next(responses)
        except StopIteration:
            return "q"

    controller = _StubController()

    monkeypatch.setattr("tgc.cli_main.bootstrap_controller", lambda env: controller)

    discover_called = {"v": False}

    def fake_discover(ctx: CommandContext):
        discover_called["v"] = True
        return {}

    monkeypatch.setattr("tgc.cli_main.command_bus.discover", fake_discover)
    monkeypatch.setattr("tgc.cli_main.command_bus.plan", lambda ctx, findings: [])
    monkeypatch.setattr("tgc.cli_main.command_bus.apply", lambda ctx, card_id: None)

    def fake_probe(self, service: str):
        if service == "drive":
            return {"service": service, "ok": True, "metadata": {"root": "root-id"}}
        if service == "sheets":
            return {"service": service, "ok": True, "metadata": {"inventory_id": "sheet-1"}}
        return {"service": service, "ok": True, "metadata": {"root": "notion-root", "pages": 3}}

    monkeypatch.setattr("core.conn_broker.ConnectionBroker.probe", fake_probe, raising=False)
    monkeypatch.setattr("core.conn_broker.ConnectionBroker.get_client", lambda self, svc, scope="read_base": types.SimpleNamespace(service=svc, scope=scope, handle=object()))

    cmd_go(fast=True, input_fn=fake_input, output_fn=outputs.append)

    assert not discover_called["v"], "Discovery should be skipped in handshake-only mode"
    assert any(line.startswith("✓ Google Drive connected") for line in outputs)
    assert any("Sheets connected" in line for line in outputs)
    assert any("Notion connected" in line for line in outputs)
