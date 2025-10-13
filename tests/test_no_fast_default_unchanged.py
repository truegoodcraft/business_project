import types

from core.bus import command_bus
from core.bus.models import CommandContext


def test_no_fast_default_unchanged(monkeypatch):
    calls = []

    def fake_load_plugin(name: str):
        module = types.SimpleNamespace(discover=lambda ctx, _name=name: calls.append(_name) or {"records": []})
        return module

    monkeypatch.setattr(command_bus, "_load_plugin", fake_load_plugin)
    monkeypatch.setattr(command_bus.plugins_json, "enabled", lambda plugin: True)

    ctx = CommandContext(controller=None, run_id="run", dry_run=False)
    result = command_bus.discover(ctx)

    assert tuple(calls) == command_bus._DISCOVERY_PLUGINS
    assert set(result.keys()) == set(command_bus._DISCOVERY_PLUGINS)
    assert ctx.extras.get("discovery_scope") == "read_crawl"
