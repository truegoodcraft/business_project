import base64
import hashlib
import os
from typing import Iterable, Optional, Tuple


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def root_signature(root: str) -> str:
    digest = hashlib.sha1(_norm(root).encode("utf-8")).hexdigest()
    return digest[:10]


def _b64e(value: str) -> str:
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _b64d(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8")).decode("utf-8")


def match_allowed_root(abs_path: str, allowed_roots: Optional[Iterable[str]]):
    """Return best matching allowed root.

    Returns tuple of (original_root, normalized_root) or None when not matched.
    """

    if abs_path is None:
        return None

    norm_path = _norm(abs_path)
    best: Optional[Tuple[str, str]] = None
    for root in allowed_roots or []:
        norm_root = _norm(root)
        # allow root itself or any child path
        if norm_path == norm_root or norm_path.startswith(norm_root.rstrip("\\/") + os.sep):
            if best is None or len(norm_root) > len(best[1]):
                best = (root, norm_root)
    return best


def to_rid(abs_path: str, allowed_roots: Optional[Iterable[str]]) -> str:
    match = match_allowed_root(abs_path, allowed_roots)
    if not match:
        raise ValueError("path_not_in_allowed_roots")
    root_orig, root_norm = match
    rel_path = os.path.relpath(_norm(abs_path), root_norm)
    return f"local:{root_signature(root_orig)}:{_b64e(rel_path)}"


def rid_to_path(rid: str, allowed_roots: Optional[Iterable[str]]) -> str:
    if not rid.startswith("local:"):
        raise ValueError("bad_rid")
    try:
        _, signature, encoded = rid.split(":", 2)
    except ValueError as exc:
        raise ValueError("bad_rid") from exc

    for root in allowed_roots or []:
        if root_signature(root) == signature:
            rel = _b64d(encoded)
            return os.path.normpath(os.path.join(root, rel))
    raise ValueError("rid_root_not_found")
