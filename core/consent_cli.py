"""Interactive helpers for managing plugin consent scopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from core.capabilities import list_caps
from core.permissions import grant as grant_scopes
import core.permissions as _permissions

_CONSENT_PATH = Path("consents.json")


def _load_consents() -> Dict[str, bool]:
    if not _CONSENT_PATH.exists():
        return {}
    try:
        return json.loads(_CONSENT_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def _write_consents(consents: Dict[str, bool]) -> None:
    _CONSENT_PATH.write_text(json.dumps(consents, indent=2))


def current_consents() -> Dict[str, List[str]]:
    consents = _load_consents()
    granted: Dict[str, List[str]] = {}
    for key, approved in consents.items():
        if not approved:
            continue
        if ":" not in key:
            continue
        plugin, scope = key.split(":", 1)
        granted.setdefault(plugin, []).append(scope)
    for plugin, scopes in granted.items():
        scopes.sort()
    return granted


def list_scopes() -> Dict[str, List[str]]:
    plugins: Dict[str, set[str]] = {}
    for metadata in list_caps().values():
        plugin = metadata.get("plugin")
        scopes = metadata.get("scopes") or []
        if not plugin:
            continue
        bucket = plugins.setdefault(str(plugin), set())
        for scope in scopes:
            bucket.add(str(scope))
    return {plugin: sorted(scope_set) for plugin, scope_set in plugins.items()}


def revoke_scopes(plugin: str, scopes: Iterable[str]) -> None:
    existing = _load_consents()
    changed = False
    for scope in scopes:
        key = f"{plugin}:{scope}"
        if key in existing:
            existing.pop(key, None)
            changed = True
        _permissions._CONSENTS.pop(key, None)
    if changed:
        _write_consents(existing)
    elif not _CONSENT_PATH.exists():
        _write_consents(existing)
