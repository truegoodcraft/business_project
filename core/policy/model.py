from enum import Enum
from pydantic import BaseModel


class Role(str, Enum):
    OWNER = "owner"
    TESTER = "tester"


class Policy(BaseModel):
    role: Role
    plan_only: bool  # Only enforced if BUS_POLICY_ENFORCE=1
