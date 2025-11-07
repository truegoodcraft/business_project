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
from typing import Any, Dict

from core.services.conn_broker import ConnectionBroker
from core.adapters.drive.provider import GoogleDriveProvider
from core.adapters.fs.provider import LocalFSProvider
from core.domain.catalog import CatalogManager


class Broker(ConnectionBroker):
    """
    Minimal broker exposed to plugins; no secrets are returned.
    Exposes:
      - logger(name)
      - service_call(provider, op, params)
      - catalog_open(source, scope, options)
      - catalog_next(stream_id, max_items)
      - catalog_close(stream_id)
    """

    def __init__(self, secrets_manager, logger_factory, capabilities, settings_reader_loader):
        super().__init__(controller=None, logger=logger_factory("broker"))
        self._secrets = secrets_manager
        self._logger_factory = logger_factory
        self.capabilities = capabilities
        self._providers = {
            "google_drive": GoogleDriveProvider(
                self._secrets, self._logger_factory, settings_reader_loader
            ),
            "local_fs": LocalFSProvider(self._logger_factory, settings_reader_loader),
        }
        self._catalog = CatalogManager(self._logger_factory, self._providers)

    def logger(self, name: str):
        return self._logger_factory(name)

    def service_call(self, provider: str, op: str, params: Dict[str, Any]) -> Dict[str, Any]:
        p = self._providers.get(provider)
        if not p:
            return {"error": "unknown_provider"}
        try:
            if op == "status" and hasattr(p, "status"):
                return p.status()
            if op == "list_children" and hasattr(p, "list_children"):
                return p.list_children(**params)
            if op == "list_drives" and hasattr(p, "list_drives"):
                return p.list_drives()
            if op == "get_start_page_token" and hasattr(p, "get_start_page_token"):
                return p.get_start_page_token()
            if op == "search" and hasattr(p, "search"):
                return p.search(**params)
            return {"error": "unknown_op"}
        except Exception:
            return {"error": "provider_error"}

    def catalog_open(self, source: str, scope: str, options: Dict[str, Any]) -> Dict[str, Any]:
        return self._catalog.open(source, scope, options)

    def catalog_next(
        self, stream_id: str, max_items: int, time_budget_ms: int = 700
    ) -> Dict[str, Any]:
        return self._catalog.next(stream_id, max_items, time_budget_ms)

    def catalog_close(self, stream_id: str) -> Dict[str, Any]:
        return self._catalog.close(stream_id)

    def clear_provider_cache(self, provider: str) -> None:
        p = self._providers.get(provider)
        if p and hasattr(p, "clear_cache"):
            try:
                p.clear_cache()
            except Exception:
                pass
