from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable
import logging
import time


@dataclass
class ClientHandle:
    service: str
    scope: str
    handle: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    issued_at: float = field(default_factory=time.time)


ProviderFn = Callable[[str], Optional[ClientHandle]]
ProbeFn = Callable[[ClientHandle | None], Dict[str, Any]]


class ConnectionBroker:
    """
    Pluggable broker. Plugins register service providers + probes.
    Core never knows Google/Notion specifics.
    """

    def __init__(self, controller: Any, *, logger: Optional[logging.Logger] = None) -> None:
        self._controller = controller
        self._logger = logger or logging.getLogger(__name__)
        self._providers: Dict[str, Dict[str, Any]] = {}
        self._grants: Dict[str, str] = {}

    def register(self, service: str, *, provider: ProviderFn, probe: ProbeFn) -> None:
        service = service.lower()
        self._providers[service] = {"provider": provider, "probe": probe}
        self._logger.info("broker.registered", extra={"service": service})

    def get_client(self, service: str, scope: str = "read_base") -> Optional[ClientHandle]:
        service = service.lower()
        scope = scope.lower()
        _order = {"read_base": 0, "read_crawl": 1, "write": 2}
        prev = self._grants.get(service)
        if prev is not None and _order.get(scope, 0) > _order.get(prev, 0):
            self._logger.warning(
                "broker.escalation.denied", extra={"service": service, "from": prev, "to": scope}
            )
            return None
        entry = self._providers.get(service)
        if not entry:
            self._logger.warning("broker.no_provider", extra={"service": service})
            return None
        handle = entry["provider"](scope)
        if handle:
            if prev is None or _order.get(scope, 0) > _order.get(prev, 0):
                self._grants[service] = scope
        return handle

    def probe(self, service: str) -> Dict[str, Any]:
        service = service.lower()
        entry = self._providers.get(service)
        if not entry:
            return {"ok": False, "detail": "no_provider", "hint": "Install a plugin that provides this service."}
        try:
            handle = entry["provider"]("read_base")
        except Exception:
            handle = None
        try:
            return entry["probe"](handle)
        except Exception as e:
            self._logger.exception("broker.probe.error")
            return {"ok": False, "detail": "probe_error", "error": str(e)}
