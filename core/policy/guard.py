import os

from fastapi import HTTPException

from .model import Role
from .store import load_policy, get_writes_enabled


def require_owner_commit() -> None:
    # Allow if env override or UI toggle is on; otherwise block
    if not get_writes_enabled():
        raise HTTPException(status_code=403, detail="Local writes disabled. Enable in Settings.")
    # Optional strict policy (OFF unless BUS_POLICY_ENFORCE=1)
    if os.environ.get("BUS_POLICY_ENFORCE") == "1":
        p = load_policy()
        if not (p.role == Role.OWNER and p.plan_only is False):
            raise HTTPException(status_code=403, detail="Commits disabled by policy (not OWNER or plan-only).")
