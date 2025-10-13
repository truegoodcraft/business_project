import json
import pathlib
import time
import hashlib


class Decision(dict):
    pass


def load_context() -> dict:
    rules_p = pathlib.Path("registry/policy.rules.yaml")
    allow_p = pathlib.Path("registry/commands.allowlist.json")
    deny_p = pathlib.Path("registry/denylist.json")
    rules_txt = rules_p.read_text() if rules_p.exists() else ""
    return {
        "allowlist": json.loads(allow_p.read_text()) if allow_p.exists() else {"commands": []},
        "rules_yaml": rules_txt,
        "denylist": json.loads(deny_p.read_text()) if deny_p.exists() else {"blocked": []},
        "policy_hash": hashlib.sha256(rules_txt.encode()).hexdigest() if rules_txt else "",
    }


def evaluate(raw_text: str, parsed_command: str, parsed_args: dict) -> Decision:
    # PLACEHOLDER: always ALLOW; no enforcement yet.
    ctx = load_context()
    return Decision(
        {
            "decision": "ALLOW",
            "command": parsed_command,
            "args": parsed_args,
            "policy_hash": ctx["policy_hash"],
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": ["placeholder-allow"],
        }
    )
