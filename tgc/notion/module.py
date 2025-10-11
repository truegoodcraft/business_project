"""Interactive Notion access module management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys
import warnings

try:
    from getpass import getpass, GetPassWarning
except ImportError:  # pragma: no cover - Python implementations without GetPassWarning
    from getpass import getpass  # type: ignore

    GetPassWarning = None  # type: ignore
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..config import NotionConfig
from .properties import build_property_payload, describe_schema

try:  # Optional dependency; module should degrade gracefully.
    from notion_client import Client
    from notion_client.errors import APIResponseError
except Exception:  # pragma: no cover - optional dependency guard
    Client = None  # type: ignore

    class APIResponseError(Exception):  # type: ignore
        """Fallback error type for environments without notion-client."""

        pass


@dataclass
class NotionModuleStatus:
    """Lightweight container describing module readiness."""

    enabled: bool
    configured: bool
    token_present: bool
    root_count: int
    client_available: bool
    client_error: Optional[str]


class NotionAccessModule:
    """Manage configuration, testing, and sampling of Notion access."""

    ENV_KEYS = (
        "NOTION_MODULE_ENABLED",
        "NOTION_API_KEY",
        "NOTION_DB_INVENTORY_ID",
        "NOTION_ROOT_IDS",
        "NOTION_PAGE_SIZE",
        "NOTION_INCLUDE_COMMENTS",
        "NOTION_INCLUDE_FILE_METADATA",
        "NOTION_MAX_DEPTH",
        "NOTION_RATE_LIMIT_QPS",
        "NOTION_TIMEOUT_SECONDS",
        "NOTION_ALLOWLIST_IDS",
        "NOTION_DENYLIST_IDS",
    )

    def __init__(self, config: NotionConfig, env_file: str | Path = ".env") -> None:
        self.config = config
        self.env_file = Path(env_file)

    # ------------------------------------------------------------------
    # Status helpers

    def status(self) -> NotionModuleStatus:
        """Return current module status including client readiness."""

        client_available = Client is not None
        client_error: Optional[str] = None
        if client_available and self.is_configured():
            try:
                Client(auth=self.config.token)  # type: ignore[call-arg]
            except Exception as exc:  # pragma: no cover - defensive guard
                client_error = str(exc)
        return NotionModuleStatus(
            enabled=self.is_enabled(),
            configured=self.is_configured(),
            token_present=bool(self.config.token),
            root_count=len(self._configured_root_ids()),
            client_available=client_available,
            client_error=client_error,
        )

    def status_lines(self) -> List[str]:
        """Return short status lines formatted for CLI display."""

        summary = self.status()
        lines = [
            f"STATUS: {'enabled' if summary.enabled else 'disabled'}",
            f"CONFIG: token={'set' if summary.token_present else 'missing'} roots={summary.root_count}",
            f"CLIENT: {'ready' if summary.client_available and not summary.client_error else 'unavailable'}",
            "SOURCE: notion_api_client",
            "MODE: read_write",
        ]
        if summary.client_error:
            lines.append(f"ERROR: {summary.client_error}")
        return lines

    def is_enabled(self) -> bool:
        return bool(self.config.module_enabled)

    def is_configured(self) -> bool:
        return self.config.is_configured()

    # ------------------------------------------------------------------
    # Interactive configuration

    def enable_interactive(self) -> Dict[str, str]:
        """Prompt the operator for configuration and persist it."""

        api_key = self._prompt_secret("Notion API key", existing=self.config.token)
        roots = self._prompt("Root IDs (comma separated)", existing=",".join(self.config.root_ids))
        inventory_db = self._prompt(
            "Inventory database ID (optional)",
            existing=self.config.inventory_database_id or (roots.split(",")[0].strip() if roots else ""),
        )
        page_size = self._safe_int(self._prompt("Page size", str(self.config.page_size or 100)), default=100)
        include_comments = self._prompt_bool("Include comments", self.config.include_comments)
        include_files = self._prompt_bool("Include file metadata", self.config.include_file_metadata)
        max_depth = self._safe_int(self._prompt("Max depth (0=unlimited)", str(self.config.max_depth)), default=0)
        rate_limit = self._safe_float(
            self._prompt("Rate limit QPS", str(self.config.rate_limit_qps)), default=self.config.rate_limit_qps
        )
        timeout = self._safe_int(
            self._prompt("Timeout seconds", str(self.config.timeout_seconds)), default=self.config.timeout_seconds
        )
        allowlist = self._prompt("Allowlist IDs (comma separated)", ",".join(self.config.allowlist_ids))
        denylist = self._prompt("Denylist IDs (comma separated)", ",".join(self.config.denylist_ids))

        root_ids = self._to_list(roots)
        allow_ids = self._to_list(allowlist)
        deny_ids = self._to_list(denylist)

        values: Dict[str, Optional[str]] = {
            "NOTION_MODULE_ENABLED": "true",
            "NOTION_API_KEY": api_key,
            "NOTION_DB_INVENTORY_ID": inventory_db or None,
            "NOTION_ROOT_IDS": ",".join(root_ids) or None,
            "NOTION_PAGE_SIZE": str(page_size),
            "NOTION_INCLUDE_COMMENTS": "true" if include_comments else "false",
            "NOTION_INCLUDE_FILE_METADATA": "true" if include_files else "false",
            "NOTION_MAX_DEPTH": str(max_depth),
            "NOTION_RATE_LIMIT_QPS": self._format_float(rate_limit),
            "NOTION_TIMEOUT_SECONDS": str(timeout),
            "NOTION_ALLOWLIST_IDS": ",".join(allow_ids) or None,
            "NOTION_DENYLIST_IDS": ",".join(deny_ids) or None,
        }

        self._persist_env(values)
        self._apply_config(
            enabled=True,
            token=api_key,
            inventory_database_id=inventory_db or None,
            root_ids=root_ids,
            page_size=page_size,
            include_comments=include_comments,
            include_file_metadata=include_files,
            max_depth=max_depth,
            rate_limit_qps=rate_limit,
            timeout_seconds=timeout,
            allowlist_ids=allow_ids,
            denylist_ids=deny_ids,
        )

        return {
            "token": self._mask_secret(api_key),
            "root_count": str(len(root_ids)),
            "inventory_database_id": self._mask_secret(inventory_db),
        }

    def disable(self) -> None:
        """Disable the module while preserving stored credentials."""

        self._persist_env({"NOTION_MODULE_ENABLED": "false"})
        self.config.module_enabled = False

    # ------------------------------------------------------------------
    # Connectivity helpers

    def test_connection(self) -> Dict[str, object]:
        """Attempt a lightweight connection check and return a report."""

        client, error = self._build_client()
        if not client:
            return {"status": "error", "detail": error}

        report: Dict[str, object] = {
            "status": "ok",
            "integration_user": None,
            "roots": [],
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "notion_api_client",
        }

        try:
            user = client.users.me()  # type: ignore[call-arg]
            report["integration_user"] = user.get("name") or user.get("bot", {}).get("owner")
        except APIResponseError as exc:  # pragma: no cover - network
            return {"status": "error", "detail": getattr(exc, "message", str(exc))}

        for root_id in self._configured_root_ids():
            report["roots"].append(self._inspect_root(client, root_id))

        return report

    def show_data(self, limit: int = 5) -> Dict[str, object]:
        """Return a small sample of data for quick inspection."""

        client, error = self._build_client()
        if not client:
            return {"status": "error", "detail": error}

        samples = []
        for root_id in self._configured_root_ids():
            samples.append(self._sample_root(client, root_id, limit))

        return {
            "status": "ok",
            "limit": limit,
            "samples": samples,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "notion_api_client",
        }

    def create_entry(self) -> Dict[str, object]:
        """Create a database entry interactively using raw value prompts."""

        client, error = self._build_client()
        if not client:
            return {"status": "error", "detail": error}

        default_db = self._default_database_id()
        database_id = self._prompt("Target database ID", existing=default_db)
        if not database_id:
            return {"status": "error", "detail": "A database ID is required."}

        try:
            database = client.databases.retrieve(database_id)  # type: ignore[arg-type]
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": getattr(exc, "message", str(exc))}

        properties = database.get("properties", {})
        if not isinstance(properties, dict):
            return {"status": "error", "detail": "Database properties unavailable."}

        field_summary = describe_schema(properties)
        if field_summary:
            print("FIELDS: " + ", ".join(field_summary))
        print("HINT: use Name=value pairs; blank line to finish.")

        assignments, warnings_list = self._collect_property_inputs(properties)
        payload, property_errors, _ = build_property_payload(properties, assignments, allow_clear=False)

        if not payload:
            detail = property_errors[0] if property_errors else "No properties supplied."
            return {
                "status": "error",
                "detail": detail,
                "warnings": warnings_list,
                "property_errors": property_errors,
            }

        try:
            page = client.pages.create(  # type: ignore[arg-type]
                parent={"database_id": database_id},
                properties=payload,
            )
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {
                "status": "error",
                "detail": getattr(exc, "message", str(exc)),
                "warnings": warnings_list,
                "property_errors": property_errors,
            }

        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return {
            "status": "ok",
            "id": page.get("id"),
            "url": page.get("url"),
            "database_id": database_id,
            "properties": list(payload.keys()),
            "warnings": warnings_list,
            "property_errors": property_errors,
            "timestamp": timestamp,
        }

    def update_entry(self) -> Dict[str, object]:
        """Update an existing Notion page interactively."""

        client, error = self._build_client()
        if not client:
            return {"status": "error", "detail": error}

        page_id = self._prompt("Page ID", existing=None)
        if not page_id:
            return {"status": "error", "detail": "A page ID is required."}

        try:
            page = client.pages.retrieve(page_id)  # type: ignore[arg-type]
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": getattr(exc, "message", str(exc))}

        properties = page.get("properties", {})
        if not isinstance(properties, dict):
            return {"status": "error", "detail": "Page properties unavailable."}

        field_summary = describe_schema(properties)
        if field_summary:
            print("FIELDS: " + ", ".join(field_summary))
        print("HINT: use Name=value pairs; type 'null' to clear; blank line to finish.")

        assignments, warnings_list = self._collect_property_inputs(properties)
        payload, property_errors, _ = build_property_payload(properties, assignments, allow_clear=True)

        if not payload and not property_errors:
            return {
                "status": "error",
                "detail": "No properties supplied.",
                "warnings": warnings_list,
                "property_errors": property_errors,
            }

        try:
            updated = client.pages.update(page_id=page_id, properties=payload)  # type: ignore[arg-type]
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {
                "status": "error",
                "detail": getattr(exc, "message", str(exc)),
                "warnings": warnings_list,
                "property_errors": property_errors,
            }

        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        parent = updated.get("parent", {}) if isinstance(updated, dict) else {}
        parent_type = parent.get("type") if isinstance(parent, dict) else None
        database_id = parent.get("database_id") if isinstance(parent, dict) else None

        return {
            "status": "ok",
            "id": updated.get("id") if isinstance(updated, dict) else None,
            "url": updated.get("url") if isinstance(updated, dict) else None,
            "parent_type": parent_type,
            "database_id": database_id,
            "properties": list(payload.keys()),
            "warnings": warnings_list,
            "property_errors": property_errors,
            "timestamp": timestamp,
        }

    # ------------------------------------------------------------------
    # Internal utilities

    def _build_client(self) -> Tuple[Optional[Client], Optional[str]]:
        if not self.is_configured():
            return None, "Module disabled or missing configuration."
        if Client is None:
            return None, "notion-client is not installed."
        try:
            client = Client(auth=self.config.token)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - defensive guard
            return None, str(exc)
        return client, None

    def _default_database_id(self) -> str:
        if self.config.inventory_database_id:
            return self.config.inventory_database_id
        roots = self._configured_root_ids()
        return roots[0] if roots else ""

    def _configured_root_ids(self) -> List[str]:
        roots = list(self.config.root_ids)
        if not roots and self.config.inventory_database_id:
            roots.append(self.config.inventory_database_id)
        seen: set[str] = set()
        ordered: List[str] = []
        for item in roots:
            if item and item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    def _inspect_root(self, client: Client, root_id: str) -> Dict[str, object]:
        try:
            database = client.databases.retrieve(root_id)  # type: ignore[arg-type]
        except APIResponseError as exc:
            if getattr(exc, "status", None) in {400, 404}:
                return self._inspect_page(client, root_id)
            return {"id": root_id, "status": "error", "detail": getattr(exc, "message", str(exc))}
        except Exception as exc:  # pragma: no cover - defensive guard
            return {"id": root_id, "status": "error", "detail": str(exc)}

        title = self._join_rich_text(database.get("title", []))
        try:
            query = client.databases.query(  # type: ignore[arg-type]
                database_id=root_id,
                page_size=min(10, self.config.page_size),
            )
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {
                "id": root_id,
                "status": "error",
                "type": "database",
                "detail": getattr(exc, "message", str(exc)),
            }
        count = len(query.get("results", []))
        has_more = bool(query.get("has_more"))
        return {
            "id": root_id,
            "status": "ok",
            "type": "database",
            "title": title,
            "objects": count,
            "has_more": has_more,
        }

    def _inspect_page(self, client: Client, root_id: str) -> Dict[str, object]:
        try:
            page = client.pages.retrieve(root_id)  # type: ignore[arg-type]
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {"id": root_id, "status": "error", "detail": getattr(exc, "message", str(exc))}

        title = self._page_title(page)
        children = client.blocks.children.list(  # type: ignore[arg-type]
            block_id=root_id,
            page_size=min(10, self.config.page_size),
        )
        return {
            "id": root_id,
            "status": "ok",
            "type": "page",
            "title": title,
            "objects": len(children.get("results", [])),
            "has_more": bool(children.get("has_more")),
        }

    def _sample_root(self, client: Client, root_id: str, limit: int) -> Dict[str, object]:
        try:
            database = client.databases.retrieve(root_id)  # type: ignore[arg-type]
        except APIResponseError:
            return self._sample_page(client, root_id, limit)

        try:
            query = client.databases.query(  # type: ignore[arg-type]
                database_id=root_id,
                page_size=min(limit, self.config.page_size),
            )
        except APIResponseError as exc:  # pragma: no cover - network dependent
            return {
                "id": root_id,
                "type": "database",
                "status": "error",
                "detail": getattr(exc, "message", str(exc)),
            }
        rows = []
        for item in query.get("results", [])[:limit]:
            properties = item.get("properties", {})
            rows.append(
                {
                    "id": item.get("id"),
                    "url": item.get("url"),
                    "edited": item.get("last_edited_time"),
                    "properties": list(properties.keys()),
                }
            )
        return {
            "id": root_id,
            "type": "database",
            "rows": rows,
            "has_more": bool(query.get("has_more")),
        }

    def _sample_page(self, client: Client, root_id: str, limit: int) -> Dict[str, object]:
        children = client.blocks.children.list(  # type: ignore[arg-type]
            block_id=root_id,
            page_size=min(limit, self.config.page_size),
        )
        blocks = []
        for block in children.get("results", [])[:limit]:
            blocks.append(
                {
                    "id": block.get("id"),
                    "type": block.get("type"),
                    "has_children": block.get("has_children"),
                    "text": self._block_text(block),
                }
            )
        return {
            "id": root_id,
            "type": "page",
            "blocks": blocks,
            "has_more": bool(children.get("has_more")),
        }

    def _block_text(self, block: Dict[str, object]) -> str:
        rich_property = block.get(block.get("type", ""), {})
        if isinstance(rich_property, dict):
            rich_text = rich_property.get("rich_text")
            if isinstance(rich_text, list):
                return self._join_rich_text(rich_text)
        return ""

    def _page_title(self, page: Dict[str, object]) -> str:
        properties = page.get("properties", {})
        if isinstance(properties, dict):
            for value in properties.values():
                if isinstance(value, dict) and value.get("type") == "title":
                    return self._join_rich_text(value.get("title", []))
        title = page.get("title")
        if isinstance(title, list):
            return self._join_rich_text(title)
        return ""

    def _join_rich_text(self, rich_text: Iterable[Dict[str, object]]) -> str:
        return "".join(str(part.get("plain_text", "")) for part in rich_text if isinstance(part, dict))

    def _apply_config(
        self,
        *,
        enabled: bool,
        token: Optional[str],
        inventory_database_id: Optional[str],
        root_ids: List[str],
        page_size: int,
        include_comments: bool,
        include_file_metadata: bool,
        max_depth: int,
        rate_limit_qps: float,
        timeout_seconds: int,
        allowlist_ids: List[str],
        denylist_ids: List[str],
    ) -> None:
        self.config.module_enabled = enabled
        self.config.token = token
        self.config.inventory_database_id = inventory_database_id
        self.config.root_ids = root_ids
        self.config.page_size = page_size
        self.config.include_comments = include_comments
        self.config.include_file_metadata = include_file_metadata
        self.config.max_depth = max_depth
        self.config.rate_limit_qps = rate_limit_qps
        self.config.timeout_seconds = timeout_seconds
        self.config.allowlist_ids = allowlist_ids
        self.config.denylist_ids = denylist_ids

    def _persist_env(self, values: Dict[str, Optional[str]]) -> None:
        editor = _EnvEditor(self.env_file)
        for key, value in values.items():
            if key not in self.ENV_KEYS:
                continue
            if value is None:
                editor.remove(key)
            else:
                editor.set(key, value)
        editor.save()

    # ------------------------------------------------------------------
    # Prompt helpers

    def _prompt(self, label: str, existing: Optional[str] = None) -> str:
        suffix = f" [{existing}]" if existing else ""
        response = input(f"INPUT: {label}{suffix}: ").strip()
        if response:
            return response
        return existing or ""

    def _prompt_secret(self, label: str, existing: Optional[str] = None) -> str:
        prompt = f"INPUT: {label}: "
        response = ""
        use_hidden = self._secret_use_hidden()

        if use_hidden:
            try:
                if GetPassWarning is not None:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=GetPassWarning)
                        response = getpass(prompt)
                else:
                    response = getpass(prompt)
            except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive guard
                raise ValueError("A Notion API key is required to enable the module.") from None
            except Exception:  # pragma: no cover - fallback for unsupported terminals
                response = ""

        if not response.strip():
            try:
                visible_prompt = f"INPUT (visible): {label}: "
                response = input(visible_prompt)
            except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive guard
                raise ValueError("A Notion API key is required to enable the module.") from None

        response = response.strip()
        if response:
            return response
        if existing:
            return existing
        raise ValueError("A Notion API key is required to enable the module.")

    def _secret_use_hidden(self) -> bool:
        """Return True if hidden secret entry should be attempted."""

        if not sys.stdin.isatty():  # pragma: no cover - non-interactive fallback
            return False

        try:
            choice = input("MODE: secret entry [h=hidden,v=visible] (h): ").strip().lower()
        except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive guard
            raise ValueError("A Notion API key is required to enable the module.") from None

        if choice in {"v", "visible", "show"}:
            return False
        return True

    def _collect_property_inputs(self, schema: Dict[str, Any]) -> Tuple[Dict[str, str], List[str]]:
        """Collect property assignments from user input."""

        assignments: Dict[str, str] = {}
        warnings_list: List[str] = []
        lookup = {name.lower(): name for name in schema.keys()}

        while True:
            try:
                raw = input("PROPERTY [Name=Value]: ").strip()
            except (EOFError, KeyboardInterrupt):  # pragma: no cover - interactive guard
                raise ValueError("Property entry cancelled.") from None

            if not raw:
                break
            if raw.lower() in {"done", "finish", "quit"}:
                break
            if "=" not in raw:
                warnings_list.append(f"Ignored input without '=': {raw}")
                print("WARN: use Name=Value format.")
                continue
            name_part, value_part = raw.split("=", 1)
            name = name_part.strip()
            value = value_part.strip()
            if not name:
                warnings_list.append("Property name missing.")
                print("WARN: property name required.")
                continue
            canonical = lookup.get(name.lower())
            if not canonical:
                warnings_list.append(f"Unknown property: {name}")
                print(f"WARN: unknown property {name}.")
                continue
            if not value:
                # Skip empty values during creation/update; clearing handled with 'null'.
                continue
            assignments[canonical] = value

        return assignments, warnings_list

    def _prompt_bool(self, label: str, existing: bool) -> bool:
        default = "y" if existing else "n"
        response = input(f"INPUT: {label} [y/n] ({default}): ").strip().lower()
        if not response:
            response = default
        return response in {"y", "yes", "1", "true"}

    def _safe_int(self, value: str, default: int) -> int:
        try:
            return int(value)
        except ValueError:
            return default

    def _safe_float(self, value: str, default: float) -> float:
        try:
            return float(value)
        except ValueError:
            return default

    def _format_float(self, value: float) -> str:
        return f"{value:.3f}".rstrip("0").rstrip(".") if value % 1 else f"{int(value)}"

    def _to_list(self, value: str) -> List[str]:
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return parts

    def _mask_secret(self, value: Optional[str]) -> str:
        if not value:
            return ""
        if len(value) <= 6:
            return "*" * len(value)
        return f"{value[:3]}***{value[-3:]}"


class _EnvEditor:
    """Minimal .env editor that preserves unrelated lines."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lines = self._read_lines()

    def set(self, key: str, value: str) -> None:
        updated = False
        prefix = f"{key}="
        for index, line in enumerate(self._lines):
            stripped = line.strip()
            if stripped.startswith(prefix):
                self._lines[index] = f"{key}={value}"
                updated = True
                break
        if not updated:
            self._lines.append(f"{key}={value}")

    def remove(self, key: str) -> None:
        prefix = f"{key}="
        self._lines = [line for line in self._lines if not line.strip().startswith(prefix)]

    def save(self) -> None:
        if not self._lines:
            self.path.write_text("", encoding="utf-8")
            return
        content = "\n".join(self._lines)
        if not content.endswith("\n"):
            content += "\n"
        self.path.write_text(content, encoding="utf-8")

    def _read_lines(self) -> List[str]:
        if not self.path.exists():
            return []
        return self.path.read_text(encoding="utf-8").splitlines()
