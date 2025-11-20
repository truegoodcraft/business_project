# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

"""Runtime boot helpers and health aggregation."""

from __future__ import annotations

import concurrent.futures
import importlib
import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    load_dotenv = None  # type: ignore

from core.brand import NAME as BRAND_NAME
from core.config import load_core_config
from core.plugin_api import Context, Result
from core.plugin_manager import load_plugins
from core.plugins_state import is_enabled as plugin_enabled
from core.safelog import logger


@dataclass
class PluginDescriptor:
    name: str
    version: Optional[str]
    path: Path
    manifest: Dict[str, Any] | None
    manifest_error: Optional[str]
    enabled: bool
    env_keys: List[str]
    missing_env: List[str]
    module: Optional[str]
    health_capability: Optional[str]
    health_timeout: Optional[float]


def _load_manifest(path: Path) -> tuple[dict | None, Optional[str]]:
    manifest_path = path / "plugin.toml"
    if not manifest_path.exists():
        return None, "plugin.toml missing"
    try:
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        return data, None
    except Exception as exc:  # pragma: no cover - defensive parse
        return None, str(exc)


def _schema_env_keys(path: Path) -> List[str]:
    schema_path = path / "config.schema.json"
    if not schema_path.exists():
        return []
    try:
        data = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    env = data.get("env")
    if isinstance(env, list):
        return [str(value) for value in env if isinstance(value, str)]
    return []


def _missing_env(keys: List[str]) -> List[str]:
    return [key for key in keys if not os.getenv(key)]


def _discover_descriptors() -> List[PluginDescriptor]:
    descriptors: List[PluginDescriptor] = []
    for plugin_path in sorted(Path("plugins").glob("*-plugin")):
        manifest, manifest_error = _load_manifest(plugin_path)
        name = (manifest or {}).get("name") or plugin_path.name
        version = (manifest or {}).get("version")
        module = None
        health_capability = None
        health_timeout: Optional[float] = None
        if manifest:
            entrypoint = manifest.get("entrypoint") or {}
            module_value = entrypoint.get("module")
            if isinstance(module_value, str):
                module = module_value
            health_section = manifest.get("health") or {}
            capability_value = health_section.get("capability")
            if isinstance(capability_value, str):
                health_capability = capability_value
            timeout_value = health_section.get("timeout_s")
            try:
                if timeout_value is not None:
                    health_timeout = float(timeout_value)
            except (TypeError, ValueError):
                health_timeout = None
        env_keys = _schema_env_keys(plugin_path)
        missing_env = _missing_env(env_keys)
        descriptors.append(
            PluginDescriptor(
                name=name,
                version=version if isinstance(version, str) else None,
                path=plugin_path,
                manifest=manifest,
                manifest_error=manifest_error,
                enabled=plugin_enabled(name),
                env_keys=env_keys,
                missing_env=missing_env,
                module=module,
                health_capability=health_capability,
                health_timeout=health_timeout,
            )
        )
    return descriptors


def _call_health(descriptor: PluginDescriptor, timeout: float) -> dict:
    if not descriptor.module:
        return {
            "capability": descriptor.health_capability,
            "status": "unknown",
            "notes": ["No entrypoint module declared"],
        }
    try:
        module = importlib.import_module(descriptor.module)
    except Exception as exc:  # pragma: no cover - import guard
        return {
            "capability": descriptor.health_capability,
            "status": "error",
            "notes": [f"Import failed: {exc}"],
        }
    health_fn = getattr(module, "health", None)
    if not callable(health_fn):
        return {
            "capability": descriptor.health_capability,
            "status": "warn",
            "notes": ["health() not implemented"],
        }

    ctx = Context(
        run_id=f"health:{descriptor.name}",
        config=load_core_config(),
        limits={},
        logger=logger,
    )

    def _invoke() -> Result:
        return health_fn(ctx)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_invoke)
        try:
            result = future.result(timeout=max(timeout, 0.1))
        except concurrent.futures.TimeoutError:
            return {
                "capability": descriptor.health_capability,
                "status": "error",
                "notes": ["Health check timed out"],
            }
        except Exception as exc:  # pragma: no cover - defensive guard
            return {
                "capability": descriptor.health_capability,
                "status": "error",
                "notes": [str(exc)],
            }

    ok_value = getattr(result, "ok", None)
    notes_value = getattr(result, "notes", None)
    notes: List[str] | None
    if isinstance(notes_value, list):
        notes = [str(n) for n in notes_value]
    elif notes_value is None:
        notes = None
    else:
        notes = [str(notes_value)]

    if ok_value is True:
        status = "ok"
    elif ok_value is False:
        status = "error"
    else:
        status = "unknown"
    return {
        "capability": descriptor.health_capability,
        "status": status,
        "notes": notes,
    }


def gather_plugin_health() -> dict:
    descriptors = _discover_descriptors()
    items: List[Dict[str, Any]] = []
    ok_count = 0
    enabled_count = 0

    for descriptor in descriptors:
        health: Dict[str, Any]
        if not descriptor.manifest:
            health = {
                "capability": None,
                "status": "error",
                "notes": [descriptor.manifest_error or "Invalid manifest"],
            }
        elif not descriptor.enabled:
            health = {
                "capability": descriptor.health_capability,
                "status": "warn",
                "notes": ["Plugin disabled"],
            }
        elif descriptor.missing_env:
            missing = ", ".join(descriptor.missing_env)
            health = {
                "capability": descriptor.health_capability,
                "status": "warn",
                "notes": [f"Missing env: {missing}"],
            }
        elif descriptor.health_capability:
            timeout = descriptor.health_timeout or 3.0
            health = _call_health(descriptor, timeout)
        else:
            health = {
                "capability": None,
                "status": "unknown",
                "notes": ["No health capability declared"],
            }

        if descriptor.enabled:
            enabled_count += 1
            if health.get("status") == "ok":
                ok_count += 1

        items.append(
            {
                "name": descriptor.name,
                "version": descriptor.version,
                "enabled": descriptor.enabled,
                "manifest_ok": bool(descriptor.manifest),
                "manifest_error": descriptor.manifest_error,
                "config": {
                    "env_keys": list(descriptor.env_keys),
                    "missing_env": list(descriptor.missing_env),
                },
                "health": {
                    "capability": health.get("capability"),
                    "status": health.get("status"),
                    "notes": health.get("notes"),
                },
                "paths": {
                    "root": str(descriptor.path),
                },
                "module": descriptor.module,
                "health_timeout": descriptor.health_timeout,
            }
        )

    return {
        "items": items,
        "summary": {
            "total": len(items),
            "enabled": enabled_count,
            "ok": ok_count,
        },
    }


def plugin_descriptors() -> List[PluginDescriptor]:
    """Return raw plugin descriptors for interactive tooling."""

    return _discover_descriptors()


def probe_plugin_health(name: str) -> Optional[dict]:
    """Run a health probe for ``name`` if available."""

    for descriptor in _discover_descriptors():
        if descriptor.name != name:
            continue
        if not descriptor.health_capability:
            return {
                "capability": None,
                "status": "unknown",
                "notes": ["No health capability declared"],
            }
        timeout = descriptor.health_timeout or 3.0
        return _call_health(descriptor, timeout)
    return None


def _check_permissions() -> bool:
    path = Path("consents.json")
    if not path.exists():
        return True
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def _check_denylist() -> bool:
    path = Path("registry/denylist.json")
    if not path.exists():
        return True
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except json.JSONDecodeError:
        return False


def _ensure_logging_path() -> tuple[bool, str]:
    log_path = Path(os.getenv("UNIFIED_LOG_PATH", "reports/all.log"))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8"):
            pass
        return True, str(log_path)
    except Exception:
        return False, str(log_path)


def gather_core_health(env_loaded: Optional[bool] = None) -> dict:
    if load_dotenv is not None and env_loaded is None:
        try:
            env_loaded = load_dotenv()
        except Exception:  # pragma: no cover - optional dependency guard
            env_loaded = False
    env_ok = bool(env_loaded)
    permissions_ok = _check_permissions()
    policy_ok = os.getenv("POLICY_PLACEHOLDER_ENABLED", "true").lower() == "true"
    denylist_ok = _check_denylist()
    logging_ok, log_path = _ensure_logging_path()

    flags = {
        "PLUGIN_SUBPROCESS": os.getenv("PLUGIN_SUBPROCESS", "false").lower() == "true",
        "OFFLINE_SAFE_MODE": os.getenv("OFFLINE_SAFE_MODE", "false").lower() == "true",
    }

    ready = env_ok and permissions_ok and policy_ok and denylist_ok and logging_ok

    return {
        "ready": ready,
        "env": {"ok": env_ok},
        "permissions": {"ok": permissions_ok},
        "policy": {"ok": policy_ok},
        "denylist": {"ok": denylist_ok},
        "isolation": {"flags": flags},
        "logging": {"ok": logging_ok, "path": log_path},
    }


def boot_sequence() -> dict:
    env_loaded = None
    if load_dotenv is not None:
        try:
            env_loaded = load_dotenv()
        except Exception:  # pragma: no cover - optional dependency guard
            env_loaded = False
    load_plugins()
    core_health = gather_core_health(env_loaded=env_loaded)
    plugin_health = gather_plugin_health()
    return {
        "brand": BRAND_NAME,
        "core": core_health,
        "plugins": plugin_health,
    }
