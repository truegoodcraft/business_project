import json
import time
import pathlib
import hashlib

from core.unilog import write as uni_write


LOG = pathlib.Path("reports/policy.log")
LOG.parent.mkdir(parents=True, exist_ok=True)


def log_policy(raw_text: str, decision: dict) -> None:
    user_hash = hashlib.sha256(raw_text.encode()).hexdigest()[:16]
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_hash": user_hash,
        "decision": decision,
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    uni_write("policy.decision", None, user_hash=user_hash, decision=decision)
