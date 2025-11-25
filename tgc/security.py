from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, Response, status

from tgc.tokens import TokenManager  # may be used for typing or future helpers
from tgc.state import AppState, get_state


async def require_token_ctx(
    request: Request,
    state: AppState = Depends(get_state),
    header_token: Optional[str] = Header(None, alias="X-Session-Token"),
) -> str:
    cookie_name = getattr(state.settings, "session_cookie_name", "bus_session")
    token = request.cookies.get(cookie_name) or header_token
    if state.tokens.check(token):
        return token or state.tokens.current()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_or_invalid_token")


def set_session_cookie(resp: Response, token: str, s) -> None:
    # starlette expects lowercase for samesite
    same_site = (getattr(s, "same_site", "lax") or "lax").lower()
    resp.set_cookie(
        key=getattr(s, "session_cookie_name", "bus_session"),
        value=token,
        httponly=True,
        samesite=same_site,
        secure=bool(getattr(s, "secure_cookie", False)),
        path="/",
        max_age=7 * 24 * 3600,
    )


def attach_session_cookie(response: Response, state: AppState) -> None:
    token = state.tokens.current()
    set_session_cookie(response, token, state.settings)
