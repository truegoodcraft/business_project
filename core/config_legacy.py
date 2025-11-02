import os
import json
import pathlib


def load_core_config() -> dict:
    return {}


def load_plugin_config(plugin: str) -> dict:
    base = {}
    schema = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if schema.exists():
        base = json.loads(schema.read_text())
    out = {}
    for k in base.get("env", []):
        v = os.getenv(k)
        if v is not None:
            out[k] = v
    return out


def plugin_env_whitelist(plugin: str) -> list[str]:
    """Return env keys this plugin is allowed to see (from its config.schema.json)."""
    schema = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if not schema.exists():
        return []
    data = json.loads(schema.read_text())
    return list(data.get("env", []))
