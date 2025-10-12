"""Google Drive adapter providing read/write helpers with dry-run safety."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

try:  # Optional dependency for environments that skip Google extras
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
except Exception:  # pragma: no cover - fallback when google-api-python-client is absent
    ServiceAccountCredentials = None  # type: ignore
    build = None  # type: ignore
    HttpError = Exception  # type: ignore
    MediaIoBaseDownload = None  # type: ignore
    MediaFileUpload = None  # type: ignore

from .base import AdapterCapability, BaseAdapter
from ..config import GoogleDriveConfig
from ..modules.google_drive import DEFAULT_MODULE_CONFIG, DriveModuleConfig

READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FULL_SCOPE = "https://www.googleapis.com/auth/drive"


def _mask(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"


def _format_http_error(error: Exception) -> str:
    if isinstance(error, HttpError):  # pragma: no branch - type guard
        try:
            payload = json.loads(error.content.decode("utf-8")) if getattr(error, "content", None) else {}
        except Exception:  # pragma: no cover - defensive
            payload = {}
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        return message or getattr(error, "message", str(error))
    return str(error)


class GoogleDriveAdapter(BaseAdapter):
    """Adapter exposing Google Drive utilities backed by stored module config."""

    name = "drive"
    implementation_state = "implemented"

    def __init__(self, config: GoogleDriveConfig) -> None:
        super().__init__(config)
        self._module_config = self._load_module_config(config)
        self._service = None
        self._client_error: Optional[str] = None
        if self._module_config.get("enabled") and self._module_config.get("credentials"):
            self._refresh_service()

    # ------------------------------------------------------------------
    # BaseAdapter overrides

    def is_configured(self) -> bool:
        roots = self._configured_root_ids()
        return bool(self._module_config.get("enabled") and self._module_config.get("credentials") and roots)

    def capabilities(self) -> List[AdapterCapability]:
        configured = self.is_configured() and self._service is not None
        allow_writes = bool(self._module_config.get("allow_writes"))
        caps = [
            AdapterCapability(
                name="Drive status",
                description="Validate credentials, quota, and reachable roots",
                configured=configured,
            ),
            AdapterCapability(
                name="File enumeration",
                description="Traverse configured roots with filtering and shortcut resolution",
                configured=configured,
            ),
        ]
        caps.append(
            AdapterCapability(
                name="Metadata & permissions updates",
                description="Apply updates with optional dry-run safety switches",
                configured=configured and allow_writes,
            )
        )
        return caps

    def metadata(self) -> Dict[str, Optional[str]]:
        credentials = self._module_config.get("credentials") or {}
        root_ids = self._configured_root_ids()
        return {
            "module_config_path": str(self.config.module_config_path or DEFAULT_MODULE_CONFIG),
            "root_ids": ", ".join(root_ids) if root_ids else None,
            "allow_writes": str(self._module_config.get("allow_writes", False)),
            "client_email": _mask(credentials.get("client_email")),
            "project_id": _mask(credentials.get("project_id")),
            "client_error": self._client_error,
        }

    def status_report(self) -> Dict[str, object]:
        report = super().status_report()
        if not self.is_configured():
            report["connection"] = {
                "status": "not_configured",
                "detail": "Enable the Drive module and provide credentials to activate the adapter.",
            }
            return report
        if self._service is None:
            report["connection"] = {"status": "error", "detail": self._client_error or "Client unavailable."}
            return report
        report["connection"] = self.verify_connection()
        return report

    # ------------------------------------------------------------------
    # Public helpers used by actions

    def verify_connection(self) -> Dict[str, object]:
        if not self.is_configured():
            return {"status": "not_configured", "detail": "Drive adapter is missing configuration."}
        service, error = self._ensure_service()
        if not service:
            return {"status": "error", "detail": error}
        try:
            about = service.about().get(fields="user,storageQuota,kind").execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        roots = self._probe_roots(service)
        return {
            "status": "ok",
            "user": about.get("user", {}),
            "storageQuota": about.get("storageQuota", {}),
            "roots": roots,
            "write_enabled": bool(self._module_config.get("allow_writes")),
        }

    def enumerate(self, *, page_size: int = 200, max_depth: int = 0) -> Iterator[Dict[str, object]]:
        """Breadth-first traversal of configured Drive roots."""

        service, error = self._ensure_service()
        if not service:
            yield {"status": "error", "detail": error}
            return
        module_data = DriveModuleConfig.from_dict(self._module_config)
        yield from self._crawl(service, module_data, page_size=page_size, max_depth=max_depth)

    def fetch_file(self, file_id: str, *, fields: str | None = None) -> Dict[str, object]:
        service, error = self._ensure_service()
        if not service:
            return {"status": "error", "detail": error}
        try:
            request = service.files().get(
                fileId=file_id,
                supportsAllDrives=True,
                fields=fields or "id, name, mimeType, size, parents, trashed, modifiedTime",
            )
            return request.execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}

    def download_file(self, file_id: str, destination: Path, *, dry_run: bool = True) -> Dict[str, object]:
        service, error = self._ensure_service()
        if not service:
            return {"status": "error", "detail": error}
        if dry_run:
            return {
                "status": "dry_run",
                "detail": f"Would download file {file_id} to {destination}",
            }
        if MediaIoBaseDownload is None:  # pragma: no cover - dependency guard
            return {
                "status": "error",
                "detail": (
                    "google-api-python-client is required to download files. "
                    "Run `pip install -r requirements.txt`."
                ),
            }
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            downloader = MediaIoBaseDownload(handle, request)
            try:
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            except Exception as exc:  # pragma: no cover - network dependent
                return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": f"Downloaded file {file_id} to {destination}"}

    def upload_file(
        self,
        source: Path,
        *,
        parent_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        dry_run: bool = True,
        overwrite: bool = False,
    ) -> Dict[str, object]:
        service, error = self._ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
        if not self._module_config.get("allow_writes"):
            return {"status": "error", "detail": "Write operations are disabled in the Drive module."}
        if dry_run:
            return {
                "status": "dry_run",
                "detail": f"Would upload {source} to parent {parent_id or 'root'}",
            }
        if MediaFileUpload is None:  # pragma: no cover - dependency guard
            return {
                "status": "error",
                "detail": (
                    "google-api-python-client is required to upload files. "
                    "Run `pip install -r requirements.txt`."
                ),
            }
        media = MediaFileUpload(source, mimetype=mime_type, resumable=True)
        body = {"name": source.name}
        if parent_id:
            body["parents"] = [parent_id]
        try:
            if overwrite:
                matches = self.find_files_by_name(source.name, parent_id=parent_id)
                if matches:
                    file_id = matches[0]["id"]
                    request = service.files().update(fileId=file_id, media_body=media)
                    response = request.execute()
                    return {"status": "ok", "detail": "Updated existing file", "file": response}
            request = service.files().create(body=body, media_body=media, fields="id, name")
            response = request.execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": "Uploaded new file", "file": response}

    def update_metadata(
        self,
        file_id: str,
        metadata: Dict[str, object],
        *,
        dry_run: bool = True,
    ) -> Dict[str, object]:
        service, error = self._ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
        if not self._module_config.get("allow_writes"):
            return {"status": "error", "detail": "Write operations are disabled in the Drive module."}
        if dry_run:
            return {
                "status": "dry_run",
                "detail": f"Would update {file_id} with metadata {metadata}",
            }
        try:
            request = service.files().update(fileId=file_id, body=metadata, supportsAllDrives=True)
            response = request.execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": "Updated metadata", "file": response}

    def find_files_by_name(self, name: str, *, parent_id: Optional[str] = None) -> List[Dict[str, object]]:
        service, error = self._ensure_service()
        if not service:
            return [{"status": "error", "detail": error}]
        query_parts = ["name = \"{}\"".format(name.replace("\"", "\\\""))]
        if parent_id:
            query_parts.append(f"'{parent_id}' in parents")
        module_data = DriveModuleConfig.from_dict(self._module_config)
        if module_data.mime_whitelist:
            mime_query = " or ".join(f"mimeType = '{mime}'" for mime in module_data.mime_whitelist)
            query_parts.append(f"({mime_query})")
        query = " and ".join(query_parts)
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    includeItemsFromAllDrives=module_data.include_shared_drives,
                    supportsAllDrives=True,
                    corpora="allDrives" if module_data.include_shared_drives else "default",
                    pageSize=module_data.page_size,
                    fields="files(id, name, mimeType, parents, modifiedTime, trashed)",
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - network dependent
            return [{"status": "error", "detail": _format_http_error(exc)}]
        return response.get("files", [])

    # ------------------------------------------------------------------
    # Internal helpers

    def _ensure_service(self, require_write: bool = False) -> Tuple[Optional[object], Optional[str]]:
        if require_write and not self._module_config.get("allow_writes"):
            return None, "Write operations are disabled; enable them in the Drive module first."
        if self._service is None or (require_write and not self._has_write_scope()):
            self._refresh_service(force_write=require_write)
        if self._service is None:
            return None, self._client_error or "Drive client unavailable."
        return self._service, None

    def _refresh_service(self, force_write: bool = False) -> None:
        if ServiceAccountCredentials is None or build is None:  # pragma: no cover - dependency guard
            self._client_error = (
                "google-api-python-client and google-auth are required. "
                "Run `pip install -r requirements.txt`."
            )
            self._service = None
            return
        if not self.is_configured():
            self._client_error = "Drive adapter is not configured."
            self._service = None
            return
        scopes = [READONLY_SCOPE]
        if self._module_config.get("allow_writes") or force_write:
            scopes = [FULL_SCOPE]
        try:
            credentials = ServiceAccountCredentials.from_service_account_info(
                self._module_config["credentials"], scopes=scopes
            )
            self._service = build("drive", "v3", credentials=credentials, cache_discovery=False)
            self._client_error = None
        except Exception as exc:  # pragma: no cover - credential issues
            self._client_error = str(exc)
            self._service = None

    def _has_write_scope(self) -> bool:
        credentials = getattr(self._service, "_http", None)
        if not credentials:
            return False
        return bool(self._module_config.get("allow_writes"))

    def _configured_root_ids(self) -> List[str]:
        roots = []
        module_roots = self._module_config.get("root_ids") or []
        if isinstance(module_roots, Iterable):
            roots.extend(str(value).strip() for value in module_roots if str(value).strip())
        if not roots and self.config.fallback_root_id:
            roots.append(self.config.fallback_root_id)
        return roots

    def _probe_roots(self, service: object) -> List[Dict[str, object]]:
        roots: List[Dict[str, object]] = []
        for root_id in self._configured_root_ids():
            try:
                result = (
                    service.files()
                    .get(
                        fileId=root_id,
                        fields="id, name, mimeType, driveId, kind",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            except Exception as exc:  # pragma: no cover - network dependent
                roots.append({"id": root_id, "status": "error", "detail": _format_http_error(exc)})
            else:
                result["status"] = "ok"
                roots.append(result)
        return roots

    def _crawl(
        self,
        service: object,
        module_data: DriveModuleConfig,
        *,
        page_size: int,
        max_depth: int,
    ) -> Iterator[Dict[str, object]]:
        from collections import deque

        visited: set[str] = set()
        queue = deque([(root_id, 0) for root_id in self._configured_root_ids()])
        mime_whitelist = set(module_data.mime_whitelist)
        include_trashed = True

        while queue:
            file_id, depth = queue.popleft()
            if file_id in visited:
                continue
            visited.add(file_id)
            try:
                file_obj = (
                    service.files()
                    .get(
                        fileId=file_id,
                        fields="id, name, mimeType, parents, trashed, driveId, kind, size, shortcutDetails",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            except Exception as exc:  # pragma: no cover - network dependent
                yield {"id": file_id, "status": "error", "detail": _format_http_error(exc)}
                continue
            yield file_obj
            mime_type = file_obj.get("mimeType")
            shortcut = file_obj.get("shortcutDetails", {})
            target_id = shortcut.get("targetId") if isinstance(shortcut, dict) else None
            if target_id and target_id not in visited:
                queue.append((target_id, depth))
                continue
            is_folder = mime_type == "application/vnd.google-apps.folder"
            if not is_folder:
                continue
            if max_depth and depth >= max_depth:
                continue
            q_parts = [f"'{file_id}' in parents"]
            if mime_whitelist:
                mime_query = " or ".join(f"mimeType = '{mime}'" for mime in mime_whitelist)
                q_parts.append(f"({mime_query})")
            if not include_trashed:
                q_parts.append("trashed = false")
            query = " and ".join(q_parts)
            page_token: Optional[str] = None
            while True:
                try:
                    response = (
                        service.files()
                        .list(
                            q=query,
                            includeItemsFromAllDrives=module_data.include_shared_drives,
                            supportsAllDrives=True,
                            corpora="allDrives" if module_data.include_shared_drives else "default",
                            pageSize=page_size,
                            pageToken=page_token,
                            fields="nextPageToken, files(id)",
                        )
                        .execute()
                    )
                except Exception as exc:  # pragma: no cover - network dependent
                    yield {
                        "parent": file_id,
                        "status": "error",
                        "detail": _format_http_error(exc),
                    }
                    break
                for child in response.get("files", []):
                    queue.append((child.get("id"), depth + 1))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

    @staticmethod
    def _load_module_config(config: GoogleDriveConfig) -> Dict[str, object]:
        path = (config.module_config_path or DEFAULT_MODULE_CONFIG).expanduser()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data


__all__ = ["GoogleDriveAdapter"]

