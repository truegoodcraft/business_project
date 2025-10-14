from __future__ import annotations
from .registry import CapabilityRegistry

# Single global registry instance for the whole process
REGISTRY = CapabilityRegistry(plugin_api_version="2")

__all__ = ["REGISTRY", "CapabilityRegistry"]
