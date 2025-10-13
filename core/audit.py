"""Audit logging utilities for capability executions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

_AUDIT_PATH = Path("reports") / "audit.log"


def _normalise_scopes(scopes: Iterable[str] | Sequence[str]) -> list[str]:
    return [str(scope) for scope in scopes]


def write_audit(
    run_id: str,
    plugin: str,
    capability: str,
    scopes: Iterable[str] | Sequence[str],
    outcome: str,
    ms: float,
) -> None:
    """Append an audit entry as a JSON line."""

    entry = {
        "run_id": run_id,
        "plugin": plugin,
        "capability": capability,
        "scopes": _normalise_scopes(scopes),
        "outcome": outcome,
        "ms": float(ms),
    }
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, separators=(",", ":")))
        handle.write("\n")
