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
