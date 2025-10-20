"""Runtime utilities for BUS Core Alpha."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.domain.broker import Broker


_BROKER: Optional["Broker"] = None


def set_broker(broker: "Broker") -> None:
    global _BROKER
    _BROKER = broker


def get_broker() -> "Broker":
    if _BROKER is None:
        raise RuntimeError("broker_not_initialized")
    return _BROKER


__all__ = ["get_broker", "set_broker"]
