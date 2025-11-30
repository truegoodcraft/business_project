from __future__ import annotations


class UseClientDefault:
    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "USE_CLIENT_DEFAULT"


USE_CLIENT_DEFAULT = UseClientDefault()

__all__ = ["USE_CLIENT_DEFAULT", "UseClientDefault"]
