# SPDX-License-Identifier: AGPL-3.0-or-later
"""Adapter registry exports."""

from .base import AdapterCapability, BaseAdapter
from .gmail import GmailAdapter
from .google_drive import GoogleDriveAdapter
from .google_sheets import GoogleSheetsAdapter
from .notion import NotionAdapter
from .wave import WaveAdapter

__all__ = [
    "AdapterCapability",
    "BaseAdapter",
    "GmailAdapter",
    "GoogleDriveAdapter",
    "GoogleSheetsAdapter",
    "NotionAdapter",
    "WaveAdapter",
]
