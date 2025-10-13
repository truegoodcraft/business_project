import time
import uuid
from typing import Any, Dict, Optional

from core.capabilities import meta, resolve
from core.config import load_core_config
from core.permissions import require
from core.plugin_api import Context
from core.safelog import logger

_RUNTIME_LIMITS: Dict[str, Any] = {}


def set_runtime_limits(limits: Dict[str, Any]) -> None:
    global _RUNTIME_LIMITS
    _RUNTIME_LIMITS = dict(limits)


def get_runtime_limits() -> Dict[str, Any]:
    return dict(_RUNTIME_LIMITS)


def generate_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ") + "-" + str(uuid.uuid4())[:8]


def run_capability(cap_name: str, run_id: Optional[str] = None, **params):
    fn = resolve(cap_name)
    m = meta(cap_name)
    require(m["plugin"], m["scopes"])
    ctx = Context(
        run_id=run_id or generate_run_id(),
        config=load_core_config(),
        limits=get_runtime_limits(),
        logger=logger,
    )
    return fn(ctx, **params)
