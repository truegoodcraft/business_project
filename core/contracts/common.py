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

"""Common contract primitives for core data transfer objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ID:
    """Strongly-typed identifier wrapper."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("ID must be a non-empty string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Timestamp:
    """Immutable timestamp container."""

    value: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.value, datetime):
            raise TypeError("Timestamp value must be a datetime instance")

    def isoformat(self) -> str:
        return self.value.isoformat()

    def __str__(self) -> str:
        return self.isoformat()


@dataclass(frozen=True)
class PathRef:
    """Filesystem path reference."""

    value: Path

    def __post_init__(self) -> None:
        if not isinstance(self.value, Path):
            raise TypeError("PathRef value must be a pathlib.Path instance")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Checksum:
    """Represents a checksum digest."""

    value: str
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("Checksum value must be a non-empty string")
        if not isinstance(self.algorithm, str) or not self.algorithm:
            raise ValueError("Checksum algorithm must be a non-empty string")

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.value}"
