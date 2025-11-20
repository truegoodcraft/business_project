# SPDX-License-Identifier: AGPL-3.0-or-later
# TGC BUS Core (Business Utility System Core)
# Copyright (C) 2025 True Good Craft
#
# This file is part of TGC BUS Core.
#
# TGC BUS Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TGC BUS Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with TGC BUS Core.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from typing import Iterable, List

from cryptography.fernet import Fernet


class _DekPool:
    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}

    def get(self, dek_id: str) -> bytes:
        if dek_id not in self._keys:
            self._keys[dek_id] = Fernet.generate_key()
        return self._keys[dek_id]


def _ensure_bytes(data) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    raise TypeError("chunk must be bytes or str")


def _to_text(data: bytes) -> str:
    return data.decode("utf-8")


_pool = _DekPool()


def encrypt(dek_id: str, chunks: Iterable) -> List[str]:
    key = _pool.get(dek_id)
    f = Fernet(key)
    out: List[str] = []
    for chunk in chunks:
        out.append(_to_text(f.encrypt(_ensure_bytes(chunk))))
    return out


def decrypt(dek_id: str, chunks: Iterable[str]) -> List[str]:
    key = _pool.get(dek_id)
    f = Fernet(key)
    out: List[str] = []
    for chunk in chunks:
        out.append(_to_text(f.decrypt(_ensure_bytes(chunk))))
    return out
