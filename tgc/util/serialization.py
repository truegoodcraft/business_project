# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serialization helpers with safety fallbacks."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _default_serializer(value: Any) -> Any:
    """Best-effort conversion for non-JSON-serializable objects."""

    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        try:
            return value.to_dict()  # type: ignore[return-value]
        except Exception:  # pragma: no cover - defensive guard
            return repr(value)
    return repr(value)


def safe_serialize(payload: Any) -> str:
    """Serialize payloads with sensible defaults for complex objects."""

    return json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        default=_default_serializer,
    )
