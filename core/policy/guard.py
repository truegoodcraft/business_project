import os

from fastapi import HTTPException

from .model import Role
from .store import load_policy


def require_owner_commit() -> None:
    # Always require explicit opt-in for any local write
    if os.environ.get("BUS_ALLOW_LOCAL_WRITES") != "1":
        raise HTTPException(status_code=403, detail="Local writes disabled (set BUS_ALLOW_LOCAL_WRITES=1).")
    # Optional policy enforcement
    if os.environ.get("BUS_POLICY_ENFORCE") == "1":
        p = load_policy()
        if not (p.role == Role.OWNER and p.plan_only is False):
            raise HTTPException(status_code=403, detail="Commits disabled by policy (not OWNER or plan-only).")
