from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

API_VERSION = "1.0"


@dataclass
class Context:
    run_id: str
    config: Dict[str, Any]
    limits: Dict[str, Any]
    logger: Any


@dataclass
class Result:
    ok: bool
    data: Any = None
    notes: List[str] | None = None


Capability = Callable[..., Result]
