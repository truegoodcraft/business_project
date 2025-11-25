from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, Response

from tgc.state import AppState, get_state


class TokenManager:
    def __init__(self) -> None:
        self._token: str = secrets.token_urlsafe(32)

    def issue(self) -> str:
        return self._token

    def validate(self, token: Optional[str]) -> bool:
        return bool(token) and secrets.compare_digest(self._token, token)


async def require_token_ctx(
    request: Request,
    state: AppState = Depends(get_state),
    header_token: Optional[str] = Header(None, alias="X-Session-Token"),
) -> str:
    token = request.cookies.get("bus_session") or header_token
    if state.tokens.validate(token):
        return token or state.tokens.issue()
    raise HTTPException(status_code=401, detail="missing_or_invalid_token")


def attach_session_cookie(response: Response, state: AppState) -> None:
    token = state.tokens.issue()
    response.set_cookie("bus_session", token, httponly=False, samesite="lax")
