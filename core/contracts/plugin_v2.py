from __future__ import annotations

from typing import Any, Dict, List, Optional


class PluginV2:
    """
    Alpha Core plugin interface (v2):
      - id: short stable id
      - name: display name
      - probe(broker) -> Dict[str, Any]: fast base-layer connectivity check
      - describe() -> Dict[str, Any]: capability metadata (scopes, services)
      - run(broker, options) -> Dict[str, Any]: optional action/processing (NOT auto-run on boot)
    """

    id: str = "plugin"
    name: str = "Alpha Plugin"

    def probe(self, broker) -> Dict[str, Any]:
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {"services": [], "scopes": ["read_base"]}

    def run(self, broker, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"ok": True}
