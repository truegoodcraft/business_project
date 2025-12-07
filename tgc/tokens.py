# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations
import secrets, hmac
from dataclasses import dataclass
from tgc.settings import Settings


@dataclass
class TokenRecord:
    token: str


class TokenManager:
    """
    Simple in-memory session token manager.
    - Generates a random token at startup
    - Allows rotation
    - Validates via constant-time comparison
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._rec = TokenRecord(token=self._new_token())

    def _new_token(self) -> str:
        return secrets.token_urlsafe(32)

    def current(self) -> str:
        return self._rec.token

    def rotate(self) -> str:
        self._rec.token = self._new_token()
        return self._rec.token

    def check(self, candidate: str | None) -> bool:
        return bool(candidate) and hmac.compare_digest(candidate, self._rec.token)
