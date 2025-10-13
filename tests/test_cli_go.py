from __future__ import annotations

from pathlib import Path
import types
from pathlib import Path
from typing import Iterator, List

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.action_cards.model import ActionCard, DiffEntry
from core.bus.models import ApplyResult, CommandContext
from tgc.cli_main import cmd_go


@pytest.fixture(autouse=True)
def _silence_stage(monkeypatch):
    monkeypatch.setattr("tgc.cli_main.stage", lambda title: 0.0)
    monkeypatch.setattr("tgc.cli_main.stage_done", lambda start: None)


def _make_cards() -> List[ActionCard]:
    safe_one = ActionCard(
        id="card-safe-1",
        kind="demo.safe",
        title="Safe action 1",
        summary="non-destructive",
        proposed_by_plugin="demo-plugin",
        diff=[],
        risk="low",
    )
    safe_two = ActionCard(
        id="card-safe-2",
        kind="demo.safe",
        title="Safe action 2",
        summary="still safe",
        proposed_by_plugin="demo-plugin",
        diff=[],
        risk="info",
    )
    destructive = ActionCard(
        id="card-danger",
        kind="demo.danger",
        title="Destructive action",
        summary="dangerous",
        proposed_by_plugin="demo-plugin",
        diff=[DiffEntry(path="foo", before="bar", after=None)],
        risk="high",
    )
    return [safe_one, safe_two, destructive]


def _install_bus(monkeypatch, cards: List[ActionCard], apply_calls: List[str]):
    def fake_bootstrap(env_file: str):  # pragma: no cover - invoked via cmd_go
        return object()

    def fake_discover(ctx: CommandContext):
        assert isinstance(ctx, CommandContext)
        return {}

    def fake_plan(ctx: CommandContext, findings):
        ctx.cards = {card.id: card for card in cards}
        return list(cards)

    def fake_apply(ctx: CommandContext, card_id: str):
        apply_calls.append(f"{ctx.run_id}:{card_id}")
        return ApplyResult(ok=True, data={"snapshot": f"reports/snapshots/{ctx.run_id}.zip"})

    monkeypatch.setattr("tgc.cli_main.bootstrap_controller", fake_bootstrap)
    monkeypatch.setattr("tgc.cli_main.command_bus.discover", fake_discover)
    monkeypatch.setattr("tgc.cli_main.command_bus.plan", fake_plan)
    monkeypatch.setattr("tgc.cli_main.command_bus.apply", fake_apply)

    class _Broker:
        def __init__(self, controller):
            self.controller = controller

        def get_client(self, service: str, scope: str = "read_base"):
            return types.SimpleNamespace(service=service, scope=scope, handle=object())

        def probe(self, service: str):
            meta = {"service": service, "ok": True, "metadata": {}}
            if service == "drive":
                meta["metadata"] = {"root": "root"}
            elif service == "sheets":
                meta["metadata"] = {"inventory_id": "sheet"}
            else:
                meta["metadata"] = {"root": "notion-root", "pages": 1}
            return meta

    monkeypatch.setattr("tgc.cli_main.ConnectionBroker", _Broker)


def test_cmd_go_applies_safe_only(monkeypatch):
    cards = _make_cards()
    apply_calls: List[str] = []
    _install_bus(monkeypatch, cards, apply_calls)

    responses = iter(["\n"])  # simulate pressing Enter
    output_log: List[str] = []

    def fake_input(prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration:
            return ""

    cmd_go(input_fn=fake_input, output_fn=output_log.append)

    assert len(apply_calls) == 2
    assert all(entry.endswith(cards[idx].id) for idx, entry in enumerate(apply_calls))
    assert any("snapshot=" in line for line in output_log)


def test_cmd_go_requires_delete_and_pin(monkeypatch):
    cards = _make_cards()
    apply_calls: List[str] = []
    _install_bus(monkeypatch, cards, apply_calls)
    monkeypatch.setenv("TGC_DELETE_PIN", "1234")

    responses: Iterator[str] = iter(["a", "DELETE", "1234"])
    output_log: List[str] = []

    def fake_input(prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration:
            return ""

    cmd_go(input_fn=fake_input, output_fn=output_log.append)

    assert len(apply_calls) == 3
    assert any(line.startswith("op_id=") for line in output_log)
