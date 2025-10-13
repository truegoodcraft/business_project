import json
import pathlib
import os


def validate_plugin_config(plugin: str) -> list[str]:
    problems = []
    p = pathlib.Path(f"plugins/{plugin}/config.schema.json")
    if not p.exists():
        problems.append(f"{plugin}: missing config.schema.json")
        return problems
    schema = json.loads(p.read_text())
    for key in schema.get("env", []):
        if not os.getenv(key):
            problems.append(f"{plugin}: missing env {key}")
    return problems
