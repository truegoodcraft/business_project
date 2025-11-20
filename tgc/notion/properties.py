# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helpers for constructing Notion property payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def describe_schema(properties: Dict[str, Any]) -> List[str]:
    """Return human-friendly descriptions of available properties."""

    descriptions: List[str] = []
    for name in sorted(properties.keys()):
        info = properties.get(name, {})
        ptype = info.get("type") if isinstance(info, dict) else None
        descriptions.append(f"{name} ({ptype or 'unknown'})")
    return descriptions


def build_property_payload(
    schema: Dict[str, Any],
    assignments: Dict[str, str],
    *,
    allow_clear: bool,
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Build a Notion property payload from raw assignments.

    Returns a tuple of (payload, errors, unmatched_fields).
    """

    payload: Dict[str, Any] = {}
    errors: List[str] = []
    unmatched: List[str] = []

    lookup = {name.lower(): name for name in schema.keys()}

    for raw_name, raw_value in assignments.items():
        canonical = lookup.get(raw_name.lower(), raw_name if raw_name in schema else None)
        if not canonical or canonical not in schema:
            unmatched.append(raw_name)
            continue
        info = schema.get(canonical, {})
        try:
            value = _coerce_property_value(info, raw_value, allow_clear=allow_clear)
        except ValueError as exc:
            errors.append(f"{canonical}: {exc}")
            continue
        if value is None:
            continue
        payload[canonical] = value

    return payload, errors, unmatched


def _coerce_property_value(property_schema: Dict[str, Any], raw_value: str, *, allow_clear: bool) -> Dict[str, Any] | None:
    ptype = property_schema.get("type")
    value = raw_value.strip()

    if not value:
        # Empty values are ignored unless clearing is explicit.
        return None

    if value.lower() in {"null", "none"}:
        if not allow_clear:
            raise ValueError("clearing is only available during updates")
        cleared = _clear_property_value(ptype)
        if cleared is None:
            raise ValueError("property type cannot be cleared")
        return cleared

    if ptype == "title":
        return {"title": _rich_text(value)}
    if ptype == "rich_text":
        return {"rich_text": _rich_text(value)}
    if ptype == "number":
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError("expected number") from exc
        return {"number": number}
    if ptype == "select":
        return {"select": {"name": value}}
    if ptype == "status":
        return {"status": {"name": value}}
    if ptype == "multi_select":
        options = [option.strip() for option in value.split(",") if option.strip()]
        return {"multi_select": [{"name": option} for option in options]}
    if ptype == "checkbox":
        lowered = value.lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return {"checkbox": True}
        if lowered in {"0", "false", "no", "n", "off"}:
            return {"checkbox": False}
        raise ValueError("expected boolean value")
    if ptype == "date":
        start, end = _split_range(value)
        return {"date": {"start": start, "end": end}}
    if ptype == "url":
        return {"url": value}
    if ptype == "email":
        return {"email": value}
    if ptype == "phone_number":
        return {"phone_number": value}
    if ptype == "relation":
        ids = [part.strip() for part in value.split(",") if part.strip()]
        return {"relation": [{"id": identifier} for identifier in ids]}
    if ptype == "people":
        ids = [part.strip() for part in value.split(",") if part.strip()]
        return {"people": [{"object": "user", "id": identifier} for identifier in ids]}

    raise ValueError(f"unsupported property type '{ptype}'")


def _clear_property_value(property_type: str | None) -> Dict[str, Any] | None:
    if property_type in {"title", "rich_text"}:
        return {property_type: []}
    if property_type == "multi_select":
        return {"multi_select": []}
    if property_type in {"select", "status"}:
        return {property_type: None}
    if property_type == "checkbox":
        return {"checkbox": False}
    if property_type == "date":
        return {"date": None}
    if property_type == "number":
        return {"number": None}
    if property_type in {"url", "email", "phone_number"}:
        return {property_type: None}
    if property_type in {"relation", "people"}:
        return {property_type: []}
    return None


def _rich_text(content: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": content}}]


def _split_range(value: str) -> Tuple[str, str | None]:
    if "->" in value:
        start, end = value.split("->", 1)
    elif "|" in value:
        start, end = value.split("|", 1)
    elif "," in value:
        start, end = value.split(",", 1)
    else:
        return value.strip(), None
    return start.strip(), end.strip() or None
