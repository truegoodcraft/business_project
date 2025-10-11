"""Base adapter interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AdapterCapability:
    """Description of an adapter capability used for planning."""

    name: str
    description: str
    configured: bool

    def as_line(self) -> str:
        status = "ready" if self.configured else "missing configuration"
        return f"{self.name}: {self.description} ({status})"


class BaseAdapter:
    """Base adapter providing status helpers."""

    name: str = "adapter"

    def __init__(self, config: object) -> None:
        self.config = config

    def is_configured(self) -> bool:
        return False

    def capabilities(self) -> List[AdapterCapability]:
        return []

    def metadata(self) -> Dict[str, Optional[str]]:
        return {}

    def describe_capabilities(self) -> List[str]:
        return [cap.as_line() for cap in self.capabilities()]
