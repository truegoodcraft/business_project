from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request

from tgc.logging_setup import setup_logging
from tgc.security import TokenManager
from tgc.settings import DATA_DIR, Settings


@dataclass
class AppState:
    settings: Settings
    core: Optional[object]
    tokens: TokenManager
    logger: object


def init_state(settings: Settings) -> AppState:
    tokens = TokenManager()
    logger = setup_logging(DATA_DIR / "buscore.log")
    return AppState(settings=settings, core=None, tokens=tokens, logger=logger)


def get_state(request: Request) -> AppState:
    state = getattr(request.app.state, "app_state", None)
    if state is None:
        raise RuntimeError("AppState not initialized")
    return state
