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
    implementation_state: str = "placeholder"

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

    # ------------------------------------------------------------------
    # Status helpers

    def is_implemented(self) -> bool:
        """Return True if the adapter has real integrations available."""

        return self.implementation_state == "implemented"

    def implementation_notes(self) -> str:
        """Human-friendly description of the adapter implementation state."""

        if self.is_implemented():
            return "Adapter provides live integrations."
        return "Adapter scaffolding ready; API integration not yet implemented."

    def status_report(self) -> Dict[str, object]:
        """Structured status summary used by status reporting commands."""

        return {
            "implemented": self.is_implemented(),
            "configured": self.is_configured(),
            "notes": self.implementation_notes(),
            "capabilities": self.describe_capabilities(),
            "metadata": self.metadata(),
        }
