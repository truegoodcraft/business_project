# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _function_source(relative_path: str, function_name: str) -> str:
    source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    return ast.get_source_segment(source, function) or ""


def test_capability_registry_honors_explicit_buscore_home_before_legacy_home() -> None:
    """Collection-time registry state must stay inside the configured root."""

    function_source = _function_source(
        "core/services/capabilities/registry.py",
        "_state_dir",
    )

    assert 'os.environ.get("BUSCORE_HOME")' in function_source
    assert 'return Path(configured_home).expanduser().resolve() / "state"' in function_source
    assert function_source.index('os.environ.get("BUSCORE_HOME")') < function_source.index("Path.home()")


def test_tgc_settings_resolves_explicit_buscore_home_before_platform_default() -> None:
    function_source = _function_source("tgc/settings.py", "_resolve_buscore_home")

    assert 'os.environ.get("BUSCORE_HOME")' in function_source
    assert "return Path(configured_home).expanduser().resolve()" in function_source
    assert function_source.index('os.environ.get("BUSCORE_HOME")') < function_source.index(
        "_platform_dirs.user_data_dir"
    )


def test_secret_store_honors_explicit_buscore_home_before_platform_fallbacks() -> None:
    function_source = _function_source("core/secrets/manager.py", "_state_dir")

    assert 'os.environ.get("BUSCORE_HOME")' in function_source
    assert 'return Path(configured_home).expanduser().resolve() / "secrets"' in function_source
    assert function_source.index('os.environ.get("BUSCORE_HOME")') < function_source.index("os.name")

    manager_source = (REPO_ROOT / "core" / "secrets" / "manager.py").read_text(encoding="utf-8")
    assert "_KEY_PATH" not in manager_source
    assert "_STORE_PATH" not in manager_source
    assert "def _key_path()" in manager_source
    assert "def _store_path()" in manager_source


def test_config_tracker_honors_explicit_buscore_home_before_platform_fallbacks() -> None:
    function_source = _function_source("core/config/tracker.py", "_state_dir")

    assert 'os.environ.get("BUSCORE_HOME")' in function_source
    assert "return Path(configured_home).expanduser().resolve()" in function_source
    assert function_source.index('os.environ.get("BUSCORE_HOME")') < function_source.index("os.name")
