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
