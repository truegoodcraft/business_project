"""Notion adapter with read/write access to the inventory vault."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

try:  # Optional dependency for environments that skip extras
    from notion_client import Client
    from notion_client.errors import APIResponseError
except Exception:  # pragma: no cover - fallback when notion-client is absent
    Client = None  # type: ignore

    class APIResponseError(Exception):  # type: ignore
        """Fallback error type so callers can handle failures uniformly."""

        pass

from .base import AdapterCapability, BaseAdapter
from ..config import NotionConfig
from ..notion.properties import build_property_payload


class NotionAdapter(BaseAdapter):
    name = "notion"
    implementation_state = "implemented"

    def __init__(self, config: NotionConfig) -> None:
        super().__init__(config)
        self._client: Optional[Client] = None
        self._client_error: Optional[str] = None
        if self.is_configured():
            if Client is None:
                self._client_error = (
                    "notion-client package is not installed. Run `pip install notion-client`."
                )
            else:
                try:
                    self._client = Client(auth=config.token)
                except Exception as exc:  # pragma: no cover - defensive guard
                    self._client_error = str(exc)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    def capabilities(self) -> List[AdapterCapability]:
        configured = self.is_configured() and self._client is not None
        return [
            AdapterCapability(
                name="Inventory (read)",
                description="Query inventory records and map to canonical fields",
                configured=configured,
            ),
            AdapterCapability(
                name="Schema introspection",
                description="Retrieve database metadata for audits",
                configured=configured,
            ),
            AdapterCapability(
                name="Inventory (write)",
                description="Create and update inventory entries via the Notion API",
                configured=configured,
            ),
        ]

    def metadata(self) -> Dict[str, Optional[str]]:
        return {
            "inventory_database_id": self.config.inventory_database_id,
            "client_error": self._client_error,
            "module_enabled": str(self.config.module_enabled).lower(),
            "root_ids": ",".join(self.config.root_ids) or None,
            "client_source": "notion_api_client" if self._client else "unavailable",
        }

    def status_report(self) -> Dict[str, object]:
        report = super().status_report()
        if self.is_configured() and self._client is not None:
            report["inventory_access"] = self.verify_inventory_access()
        return report

    # ------------------------------------------------------------------
    # Public helpers used by actions

    def verify_inventory_access(self) -> Dict[str, object]:
        """Return metadata about the configured inventory database."""

        if not self.is_configured():
            return {"status": "not_configured", "detail": "Inventory module disabled or missing configuration."}
        database_id = self._primary_database_id()
        if not database_id:
            return {"status": "error", "detail": "No database or root ID supplied."}
        client, error = self._get_client()
        if not client:
            return {"status": "error", "detail": error}
        try:
            database = client.databases.retrieve(database_id)  # type: ignore[arg-type]
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": getattr(exc, "message", str(exc))}
        title = self._join_rich_text(database.get("title", []))
        properties = list(database.get("properties", {}).keys())
        preview = self.fetch_inventory_preview(limit=3)
        return {
            "status": "ok",
            "title": title,
            "property_count": len(properties),
            "properties": properties,
            "preview_sample": preview,
        }

    def fetch_inventory_preview(self, limit: int = 10) -> List[Dict[str, Optional[str]]]:
        """Return up to ``limit`` inventory rows mapped to canonical fields."""

        client, error = self._get_client()
        if not client:
            return [{"status": error}]
        database_id = self._primary_database_id()
        if not database_id:
            return [{"status": "No database configured."}]
        try:
            response = client.databases.query(  # type: ignore[arg-type]
                database_id=database_id,
                page_size=min(limit, self.config.page_size),
            )
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return [{"status": getattr(exc, "message", str(exc))}]
        results = response.get("results", [])
        mapped: List[Dict[str, Optional[str]]] = []
        for page in results:
            mapped.append(self._map_inventory_page(page))
        return mapped

    def create_inventory_entry(
        self, assignments: Dict[str, str], database_id: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """Create a database entry using raw property assignments."""

        client, error = self._get_client()
        if not client:
            raise RuntimeError(error or "Notion client unavailable")
        target_db = database_id or self._primary_database_id()
        if not target_db:
            raise ValueError("A database ID is required.")
        schema = client.databases.retrieve(target_db)  # type: ignore[arg-type]
        properties = schema.get("properties", {})
        payload, errors, unmatched = build_property_payload(
            properties if isinstance(properties, dict) else {},
            assignments,
            allow_clear=False,
        )
        issues = list(errors)
        issues.extend(f"{name}: unknown property" for name in unmatched)
        if issues:
            raise ValueError("; ".join(issues))
        if not payload:
            raise ValueError("No valid properties supplied.")
        page = client.pages.create(  # type: ignore[arg-type]
            parent={"database_id": target_db},
            properties=payload,
        )
        return {
            "id": page.get("id"),
            "url": page.get("url"),
            "database_id": target_db,
            "properties": ",".join(payload.keys()) or None,
        }

    def update_page_properties(self, page_id: str, assignments: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Update properties on an existing page."""

        client, error = self._get_client()
        if not client:
            raise RuntimeError(error or "Notion client unavailable")
        page = client.pages.retrieve(page_id)  # type: ignore[arg-type]
        properties = page.get("properties", {})
        payload, errors, unmatched = build_property_payload(
            properties if isinstance(properties, dict) else {},
            assignments,
            allow_clear=True,
        )
        issues = list(errors)
        issues.extend(f"{name}: unknown property" for name in unmatched)
        if issues:
            raise ValueError("; ".join(issues))
        if not payload:
            raise ValueError("No valid properties supplied.")
        updated = client.pages.update(page_id=page_id, properties=payload)  # type: ignore[arg-type]
        parent = updated.get("parent", {}) if isinstance(updated, dict) else {}
        database_id = parent.get("database_id") if isinstance(parent, dict) else None
        return {
            "id": updated.get("id") if isinstance(updated, dict) else None,
            "url": updated.get("url") if isinstance(updated, dict) else None,
            "database_id": database_id,
            "properties": ",".join(payload.keys()) or None,
        }

    def implementation_notes(self) -> str:
        if not self.is_configured():
            return "Notion adapter ready; enable the Notion access module with credentials for read/write access."
        if self._client_error:
            return f"Configured but cannot initialise client: {self._client_error}"
        return "Supports live, read/write access to the Vault inventory database."

    # ------------------------------------------------------------------
    # Internal utilities

    def _get_client(self) -> Tuple[Optional[Client], str | None]:
        if not self.is_configured():
            return None, "Notion adapter is not configured."
        if self._client is None:
            return None, self._client_error or "Notion client is unavailable."
        return self._client, None

    def _primary_database_id(self) -> Optional[str]:
        if self.config.inventory_database_id:
            return self.config.inventory_database_id
        if self.config.root_ids:
            return self.config.root_ids[0]
        return None

    def _map_inventory_page(self, page: Dict[str, Any]) -> Dict[str, Optional[str]]:
        properties = page.get("properties", {})
        return {
            "id": page.get("id"),
            "name": self._extract_property(properties, ["Name", "name", "Title"]),
            "sku": self._extract_property(properties, ["SKU", "sku", "Item", "Item ID"]),
            "qty": self._extract_property(properties, ["Qty", "Quantity", "qty"]),
            "batch": self._extract_property(properties, ["Batch", "Lot", "batch"]),
            "notes": self._extract_property(properties, ["Notes", "notes", "Description"]),
            "url": page.get("url"),
            "last_edited_time": page.get("last_edited_time"),
        }

    def _extract_property(self, properties: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
        for key in keys:
            if key in properties:
                return self._property_to_string(properties[key])
        return None

    def _property_to_string(self, prop: Dict[str, Any]) -> Optional[str]:
        if not prop:
            return None
        ptype = prop.get("type")
        if ptype == "title":
            return self._join_rich_text(prop.get("title", [])) or None
        if ptype == "rich_text":
            return self._join_rich_text(prop.get("rich_text", [])) or None
        if ptype == "number":
            number = prop.get("number")
            return str(number) if number is not None else None
        if ptype == "select":
            option = prop.get("select")
            return option.get("name") if option else None
        if ptype == "multi_select":
            options = prop.get("multi_select", [])
            names = ", ".join(option.get("name", "") for option in options if option.get("name"))
            return names or None
        if ptype == "checkbox":
            return "true" if prop.get("checkbox") else "false"
        if ptype == "date":
            date = prop.get("date") or {}
            start = date.get("start")
            end = date.get("end")
            if start and end:
                return f"{start} → {end}"
            return start or end
        if ptype == "formula":
            formula = prop.get("formula", {})
            for key in ("string", "number", "boolean"):
                value = formula.get(key)
                if value is not None:
                    return str(value)
            return None
        if ptype == "rollup":
            rollup = prop.get("rollup", {})
            if rollup.get("type") == "array":
                return ", ".join(
                    self._join_rich_text(item.get("rich_text", []))
                    if isinstance(item, dict)
                    else str(item)
                    for item in rollup.get("array", [])
                ) or None
            return str(rollup.get(rollup.get("type", ""))) if rollup else None
        if ptype == "people":
            people = prop.get("people", [])
            return ", ".join(person.get("name", "") for person in people if person.get("name")) or None
        if ptype == "relation":
            relation = prop.get("relation", [])
            return ", ".join(item.get("id", "") for item in relation if item.get("id")) or None
        return None

    def _join_rich_text(self, rich_text: Iterable[Dict[str, Any]]) -> str:
        return "".join(part.get("plain_text", "") for part in rich_text)
