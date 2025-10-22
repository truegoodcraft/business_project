import json
import os
import pathlib

from .model import Policy, Role

CONFIG_DIR = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "BUSCore"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_POLICY = Policy(role=Role.OWNER, plan_only=False)  # framework present, OFF by default


def load_policy() -> Policy:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            role = Role(data.get("role", DEFAULT_POLICY.role))
            plan_only = bool(data.get("plan_only", DEFAULT_POLICY.plan_only))
            return Policy(role=role, plan_only=plan_only)
        except Exception:
            pass
    return DEFAULT_POLICY


def save_policy(policy: Policy) -> None:
    CONFIG_FILE.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
