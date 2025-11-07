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

"""Helpers for discovering duplicate files within allowed roots."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Dict, Iterator, List


@dataclass
class FileInfo:
    """Snapshot of a file encountered during a walk."""

    path: str
    size: int
    mtime: float


def iter_files(root: str) -> Iterator[FileInfo]:
    """Yield files under ``root`` along with metadata."""

    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            full_path = os.path.join(dirpath, name)
            try:
                stat = os.stat(full_path)
            except OSError:
                # File may disappear or be inaccessible; skip best-effort.
                continue
            yield FileInfo(full_path, stat.st_size, stat.st_mtime)


def sha256_of(path: str, bufsize: int = 1024 * 1024) -> str:
    """Return SHA-256 digest for ``path`` using buffered reads."""

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(bufsize)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(start_root: str) -> Dict[str, List[str]]:
    """Return mapping of sha256 digest -> duplicate file paths."""

    size_buckets: Dict[int, List[str]] = {}
    for info in iter_files(start_root):
        size_buckets.setdefault(info.size, []).append(info.path)

    duplicates: Dict[str, List[str]] = {}
    for paths in size_buckets.values():
        if len(paths) < 2:
            continue
        digest_groups: Dict[str, List[str]] = {}
        for path in paths:
            try:
                digest = sha256_of(path)
            except (OSError, IOError):
                continue
            digest_groups.setdefault(digest, []).append(path)
        for digest, group in digest_groups.items():
            if len(group) > 1:
                duplicates[digest] = group
    return duplicates


def pick_keeper(paths: List[str]) -> str:
    """Pick the file to keep among duplicates.

    The oldest modification time wins; ties fall back to shortest path length.
    Missing files are treated as newest so healthy files win.
    """

    ranked: List[tuple[float, int, str]] = []
    for path in paths:
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            mtime = float("inf")
        ranked.append((mtime, len(path), path))
    ranked.sort()
    return ranked[0][2] if ranked else ""
