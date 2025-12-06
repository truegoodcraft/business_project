from __future__ import annotations

from fastapi import HTTPException, Request, Response, status

from tgc.tokens import TokenManager  # reserved for typing/future helpers
from tgc.state import get_state


async def require_token_ctx(request: Request):
    state = get_state(request)
    s = state.settings
    tok = getattr(request.state, "session", None) or request.cookies.get(s.session_cookie_name) or request.cookies.get("session") or request.cookies.get("sessionid")
    if not state.tokens.check(tok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return None  # context placeholder


def set_session_cookie(resp: Response, token: str, s) -> None:
    # starlette expects lowercase for samesite
    same_site = (getattr(s, "same_site", "lax") or "lax").lower()
    resp.set_cookie(
        key=s.session_cookie_name,
        value=token,
        httponly=True,
        samesite=same_site,
        secure=bool(getattr(s, "secure_cookie", False)),
        path="/",
        max_age=7 * 24 * 3600,
    )


# Back-compat alias for older imports
attach_session_cookie = set_session_cookie
