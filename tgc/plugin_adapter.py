"""Compatibility shims for plugin instances."""

from __future__ import annotations

from typing import Any, Dict


class _V1Shim:
    """Best-effort shim that exposes v1 call signatures."""

    api_version = "1.0"

    def __init__(self, plugin: Any, original_version: str) -> None:
        self._plugin = plugin
        self._original_version = original_version

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._plugin, name)

    def propose(self, ctx: Dict[str, object], input_data: Dict[str, object]):
        if hasattr(self._plugin, "propose"):
            return self._plugin.propose(ctx, input_data)
        if hasattr(self._plugin, "plan"):
            return self._plugin.plan(ctx=ctx, input=input_data)
        raise AttributeError("Plugin does not implement propose/plan for API compatibility")

    def apply(self, ctx: Dict[str, object], card):
        if hasattr(self._plugin, "apply"):
            return self._plugin.apply(ctx, card)
        if hasattr(self._plugin, "execute"):
            return self._plugin.execute(ctx=ctx, card=card)
        raise AttributeError("Plugin does not implement apply/execute for API compatibility")

    def rollback(self, ctx: Dict[str, object], op_snapshot: Dict[str, object]):
        if hasattr(self._plugin, "rollback"):
            return self._plugin.rollback(ctx, op_snapshot)
        if hasattr(self._plugin, "undo"):
            return self._plugin.undo(ctx=ctx, snapshot=op_snapshot)
        return {"ok": False, "notes": ["Rollback not implemented"]}

    def health(self) -> Dict[str, object]:
        if hasattr(self._plugin, "health"):
            return self._plugin.health()
        return {
            "status": "unknown",
            "notes": [f"Plugin API {self._original_version} lacks health()"],
        }


def adapt(plugin: Any) -> Any:
    """Adapt ``plugin`` to the v1 interface when necessary."""

    version = getattr(plugin, "api_version", None)
    if version is None:
        return plugin
    version_str = str(version)
    if version_str.startswith("1."):
        return plugin
    return _V1Shim(plugin, version_str)


__all__ = ["adapt"]
