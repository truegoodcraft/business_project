from __future__ import annotations

import builtins
import importlib
import importlib.util
import pkgutil
import sys
from contextlib import contextmanager
from typing import Iterator, List, Set

from core.contracts.plugin_v2 import PluginV2
from core.public_api import PUBLIC_IMPORTS_ALLOWLIST


def _is_allowed_core_module(module_name: str) -> bool:
    if module_name == "core":
        return False
    for allowed in PUBLIC_IMPORTS_ALLOWLIST:
        if module_name == allowed or module_name.startswith(f"{allowed}."):
            return True
    return False


def _disallowed_new_core_imports(before: Set[str], after: Set[str]) -> Set[str]:
    newly = {name for name in after - before if name.startswith("core.")}
    return {name for name in newly if not _is_allowed_core_module(name)}


@contextmanager
def _capture_plugin_imports(prefix: str) -> Iterator[Set[str]]:
    captured: Set[str] = set()
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[override]
        importer = None
        if isinstance(globals, dict):
            importer = globals.get("__name__")
        if importer and importer.startswith(prefix):
            resolved = name
            if level and isinstance(globals, dict):
                package = globals.get("__package__") or importer
                try:
                    resolved = importlib.util.resolve_name(name or "", package)
                except Exception:
                    resolved = name
            captured.add(resolved)
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    try:
        yield captured
    finally:
        builtins.__import__ = original_import


def _disallowed_captured_imports(prefix: str, captured: Set[str]) -> Set[str]:
    violations: Set[str] = set()
    for name in captured:
        if not name:
            continue
        absolute = name if not name.startswith(".") else f"{prefix}{name}"
        if absolute == "core" or absolute.startswith("core."):
            if not _is_allowed_core_module(absolute):
                violations.add(absolute)
    return violations


def discover_alpha_plugins() -> List[PluginV2]:
    plugins: List[PluginV2] = []
    for _, name, _ in pkgutil.iter_modules(["plugins_alpha"]):
        if name.startswith("_"):
            continue
        mod = None
        snap_before = set(sys.modules.keys())
        prefix = f"plugins_alpha.{name}"
        captured_names: Set[str] = set()
        try:
            for candidate in (f"{prefix}.plugin", prefix):
                with _capture_plugin_imports(prefix) as captured:
                    try:
                        mod = importlib.import_module(candidate)
                        captured_names = set(captured)
                        break
                    except Exception:
                        mod = None
                        captured_names = set()
                        continue
                # context manager ensures restore even on exception
            if mod is None:
                continue
            snap_after = set(sys.modules.keys())
            captured_violations = _disallowed_captured_imports(prefix, captured_names)
            module_violations = _disallowed_new_core_imports(snap_before, snap_after)
            violations = captured_violations | module_violations
            if violations:
                newly_loaded = snap_after - snap_before
                for module_name in newly_loaded:
                    if module_name.startswith(prefix):
                        sys.modules.pop(module_name, None)
                for module_name in newly_loaded:
                    if module_name.startswith("core."):
                        sys.modules.pop(module_name, None)
                continue
            cls = getattr(mod, "Plugin", None)
            if cls and issubclass(cls, PluginV2):
                plugins.append(cls())
        except Exception:
            continue
    return plugins
