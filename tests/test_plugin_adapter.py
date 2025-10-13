from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tgc.plugin_adapter import adapt


class LegacyPlugin:
    def propose(self, ctx, input_data):
        return ["ok", ctx, input_data]

    def apply(self, ctx, card):
        return {"diff_applied": True, "card": card}

    def rollback(self, ctx, op_snapshot):  # pragma: no cover - exercise optional path
        return {"rolled_back": True}

    def health(self):
        return {"status": "ok"}


def test_adapt_defaults_to_v1():
    plugin = LegacyPlugin()
    adapted = adapt(plugin)
    assert adapted is plugin
    assert getattr(adapted, "api_version", "1.0") == "1.0"
    assert adapted.propose({"k": 1}, {"input": True})[0] == "ok"
    assert adapted.apply({}, {"card": 1})["diff_applied"] is True
    assert adapted.health()["status"] == "ok"
