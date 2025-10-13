"""Configuration loading helpers for the controller core and plugins."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any


def load_core_config() -> Dict[str, Any]:
    """Return configuration values required by the core system."""
    return {}


def load_plugin_config(plugin: str) -> Dict[str, str]:
    """Load configuration for a plugin based on its schema and environment.

    Parameters
    ----------
    plugin:
        The plugin folder name under the ``plugins`` directory.

    Returns
    -------
    dict
        A mapping of environment variable names to their resolved values. Only
        variables declared in the plugin's ``config.schema.json`` file are
        considered. Missing environment variables are omitted from the result.
    """

    schema_path = Path("plugins") / plugin / "config.schema.json"

    base: Dict[str, Any] = {}
    if schema_path.exists():
        base = json.loads(schema_path.read_text())

    env_vars = base.get("env", []) if isinstance(base, dict) else []

    resolved: Dict[str, str] = {}
    for key in env_vars:
        value = os.getenv(key)
        if value is not None:
            resolved[key] = value

    return resolved
