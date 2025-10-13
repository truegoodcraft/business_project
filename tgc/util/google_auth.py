"""Utilities for working with Google authenticated sessions."""

from __future__ import annotations

import os
from typing import Final, Iterable

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

_SCOPES: Final[Iterable[str]] = (
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
)


def google_session(creds_path: str | None = None) -> AuthorizedSession:
    """Return an :class:`AuthorizedSession` authenticated as a service account.

    Args:
        creds_path: Optional path to a Google service account JSON credentials
            file. When omitted, :envvar:`GOOGLE_APPLICATION_CREDENTIALS` is
            used.

    Raises:
        RuntimeError: Raised when no credentials path can be resolved.

    Returns:
        An :class:`AuthorizedSession` scoped for Drive and Sheets read access.
    """

    resolved_path = creds_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not resolved_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set")

    credentials = service_account.Credentials.from_service_account_file(
        resolved_path, scopes=_SCOPES
    )
    return AuthorizedSession(credentials)

