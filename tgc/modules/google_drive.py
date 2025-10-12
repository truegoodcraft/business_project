"""Interactive Google Drive module configuration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:  # Optional dependency to keep base installs light
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except Exception:  # pragma: no cover - fallback when Google libraries are absent
    ServiceAccountCredentials = None  # type: ignore
    build = None  # type: ignore
    HttpError = Exception  # type: ignore
    MediaFileUpload = None  # type: ignore

DEFAULT_MODULE_CONFIG = Path("config/google_drive_module.json")
READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
FULL_SCOPE = "https://www.googleapis.com/auth/drive"


@dataclass
class DriveModuleConfig:
    """Persisted configuration for the Google Drive module."""

    enabled: bool = False
    credentials: Dict[str, object] = field(default_factory=dict)
    credentials_path: str = ""
    root_ids: List[str] = field(default_factory=list)
    include_shared_with_me: bool = False
    include_shared_drives: bool = True
    mime_whitelist: List[str] = field(default_factory=list)
    page_size: int = 200
    max_depth: int = 0
    rate_limit_qps: int = 3
    timeout_seconds: int = 30
    allow_writes: bool = False

    def has_credentials(self) -> bool:
        return bool(self.credentials)

    def scopes(self, require_write: bool = False) -> List[str]:
        if require_write or self.allow_writes:
            return [FULL_SCOPE]
        return [READONLY_SCOPE]

    def all_root_ids(self, fallback: Optional[Iterable[str] | str] = None) -> List[str]:
        roots = [value for value in (self.root_ids or []) if value]
        if fallback:
            if isinstance(fallback, str):
                extra = [fallback]
            else:
                extra = [value for value in fallback if value]
            for value in extra:
                if value and value not in roots:
                    roots.append(value)
        return roots

    def to_dict(self) -> Dict[str, object]:
        return {
            "enabled": self.enabled,
            "credentials": self.credentials,
            "credentials_path": self.credentials_path,
            "root_ids": list(self.root_ids),
            "include_shared_with_me": self.include_shared_with_me,
            "include_shared_drives": self.include_shared_drives,
            "mime_whitelist": list(self.mime_whitelist),
            "page_size": self.page_size,
            "max_depth": self.max_depth,
            "rate_limit_qps": self.rate_limit_qps,
            "timeout_seconds": self.timeout_seconds,
            "allow_writes": self.allow_writes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "DriveModuleConfig":
        config = cls()
        config.enabled = bool(data.get("enabled", config.enabled))
        credentials_raw = data.get("credentials")
        if isinstance(credentials_raw, dict):
            config.credentials = credentials_raw
        config.credentials_path = str(data.get("credentials_path", config.credentials_path or ""))
        if not config.credentials and config.credentials_path:
            # Support legacy configs that only stored a path to import from.
            path = Path(config.credentials_path).expanduser()
            if path.exists():
                try:
                    config.credentials = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    config.credentials = {}
        config.root_ids = _clean_list(data.get("root_ids"), allow_empty=True)
        config.include_shared_with_me = bool(data.get("include_shared_with_me", config.include_shared_with_me))
        config.include_shared_drives = bool(data.get("include_shared_drives", config.include_shared_drives))
        config.mime_whitelist = _clean_list(data.get("mime_whitelist"))
        config.page_size = int(data.get("page_size", config.page_size))
        config.max_depth = int(data.get("max_depth", config.max_depth))
        config.rate_limit_qps = int(data.get("rate_limit_qps", config.rate_limit_qps))
        config.timeout_seconds = int(data.get("timeout_seconds", config.timeout_seconds))
        config.allow_writes = bool(data.get("allow_writes", config.allow_writes))
        return config


class GoogleDriveModule:
    """Self-contained helper that manages Google Drive configuration."""

    def __init__(
        self,
        config: DriveModuleConfig,
        config_path: Path = DEFAULT_MODULE_CONFIG,
        *,
        fallback_root_id: Optional[str] = None,
        shared_drive_id: Optional[str] = None,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.fallback_root_id = fallback_root_id
        self.shared_drive_id = shared_drive_id
        self._validation_errors: List[str] = []
        self._validation_notes: List[str] = []
        self._corpora_mode = self._determine_corpora_mode()
        self._validate_environment()

    # ------------------------------------------------------------------
    # Drive client helpers

    def root_ids(self) -> List[str]:
        return self.config.all_root_ids()

    def corpora_mode(self) -> str:
        return self._corpora_mode

    def validation_details(self) -> Dict[str, List[str]]:
        return {
            "notes": list(self._validation_notes),
            "errors": list(self._validation_errors),
        }

    def ensure_service(self, *, require_write: bool = False) -> Tuple[Optional[object], Optional[str]]:
        if ServiceAccountCredentials is None or build is None:  # pragma: no cover - dependency guard
            return None, (
                "google-api-python-client and google-auth are required. "
                "Run `pip install -r requirements.txt`."
            )
        if not self.config.enabled:
            return None, "Drive module is disabled."
        if not self.config.has_credentials():
            return None, "No credentials stored; import a service account JSON first."
        try:
            credentials = ServiceAccountCredentials.from_service_account_info(
                self.config.credentials,
                scopes=self.config.scopes(require_write=require_write),
            )
        except Exception as exc:  # pragma: no cover - credential parsing guard
            return None, f"Unable to load credentials: {exc}"
        try:
            service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        except Exception as exc:  # pragma: no cover - dependency guard
            return None, f"Unable to initialise Drive client: {exc}"
        return service, None

    # ------------------------------------------------------------------
    # Validation helpers

    def validation_summary(self) -> List[str]:
        lines: List[str] = []
        description = self._describe_corpora_mode()
        lines.append(f"Corpora mode: {description}")
        if self.shared_drive_id:
            lines.append(f"Shared drive ID: {self.shared_drive_id}")
        if self.fallback_root_id:
            lines.append(f"Fallback root (DRIVE_ROOT_FOLDER_ID): {self.fallback_root_id}")
        if self._validation_errors:
            lines.append("Validation errors detected:")
            lines.extend(f"  • {message}" for message in self._validation_errors)
        elif self._validation_notes:
            lines.append("Validation checks:")
            lines.extend(f"  • {message}" for message in self._validation_notes)
        return lines

    # ------------------------------------------------------------------
    # Persistence helpers

    @classmethod
    def load(
        cls,
        path: Path = DEFAULT_MODULE_CONFIG,
        *,
        fallback_root_id: Optional[str] = None,
        shared_drive_id: Optional[str] = None,
    ) -> "GoogleDriveModule":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        config = DriveModuleConfig.from_dict(data)
        return cls(
            config=config,
            config_path=path,
            fallback_root_id=fallback_root_id,
            shared_drive_id=shared_drive_id,
        )

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._validate_environment()

    # ------------------------------------------------------------------
    # Status helpers

    def is_enabled(self) -> bool:
        return self.config.enabled

    def status_summary(self) -> List[str]:
        lines = ["Google Drive module status:"]
        lines.append(f"- Enabled: {'yes' if self.config.enabled else 'no'}")
        if self.config.has_credentials():
            lines.append("- Credentials: stored (service account JSON)")
            client_email = _mask_value(str(self.config.credentials.get("client_email", "")))
            project_id = _mask_value(str(self.config.credentials.get("project_id", "")))
            if client_email:
                lines.append(f"  • Service account: {client_email}")
            if project_id:
                lines.append(f"  • Project: {project_id}")
        else:
            lines.append("- Credentials: not captured yet")
        roots = self.root_ids()
        if roots:
            lines.append(f"- Root IDs ({len(roots)}): {', '.join(roots)}")
        else:
            lines.append("- Root IDs: not configured")
        if self.fallback_root_id:
            lines.append(f"- Fallback root (DRIVE_ROOT_FOLDER_ID): {self.fallback_root_id}")
        lines.append(f"- Corpora mode: {self._describe_corpora_mode()}")
        lines.append(
            f"- Include 'Shared with me': {'yes' if self.config.include_shared_with_me else 'no'}"
        )
        lines.append(f"- Include shared drives: {'yes' if self.config.include_shared_drives else 'no'}")
        if self.shared_drive_id:
            lines.append(f"  • Shared drive ID: {self.shared_drive_id}")
        if self.config.mime_whitelist:
            lines.append(f"- MIME whitelist: {', '.join(self.config.mime_whitelist)}")
        else:
            lines.append("- MIME whitelist: all types")
        lines.append(f"- Allow write operations: {'yes' if self.config.allow_writes else 'no'}")
        lines.append(f"- Config file: {self._mask_path(str(self.config_path))}")
        if self._validation_errors:
            lines.append("- Validation errors:")
            lines.extend(f"  • {message}" for message in self._validation_errors)
        elif self._validation_notes:
            lines.append("- Validation checks:")
            lines.extend(f"  • {message}" for message in self._validation_notes)
        return lines

    def preview_data(self) -> List[str]:
        lines = ["Google Drive module configuration snapshot:"]
        lines.append(f"Enabled: {self.config.enabled}")
        lines.append(
            f"Credentials stored: {'yes' if self.config.has_credentials() else 'no'}"
        )
        if self.config.has_credentials():
            lines.extend(self._credential_preview())
        lines.append(f"Allow write operations: {self.config.allow_writes}")
        lines.append(f"Include shared drives: {self.config.include_shared_drives}")
        lines.append(f"Include 'Shared with me': {self.config.include_shared_with_me}")
        lines.append(f"Page size: {self.config.page_size}")
        lines.append(f"Traversal depth limit: {self.config.max_depth or 'unlimited'}")
        lines.append(f"Rate limit QPS: {self.config.rate_limit_qps}")
        lines.append(f"Timeout seconds: {self.config.timeout_seconds}")
        roots = self.root_ids()
        if roots:
            lines.append("Configured root IDs:")
            lines.extend(f"  - {value}" for value in roots)
        else:
            lines.append("Configured root IDs: (none)")
        if self.fallback_root_id:
            lines.append(f"Fallback root (DRIVE_ROOT_FOLDER_ID): {self.fallback_root_id}")
        lines.append(f"Corpora mode: {self._describe_corpora_mode()}")
        if self.shared_drive_id:
            lines.append(f"Shared drive ID: {self.shared_drive_id}")
        if self.config.mime_whitelist:
            lines.append("MIME whitelist:")
            lines.extend(f"  - {value}" for value in self.config.mime_whitelist)
        else:
            lines.append("MIME whitelist: (all)")
        if self.config.credentials_path:
            lines.append(
                f"Original credentials file: {self._mask_path(self.config.credentials_path)}"
            )
        lines.append(f"Configuration stored at: {self._mask_path(str(self.config_path))}")
        if self._validation_errors:
            lines.append("Validation errors:")
            lines.extend(f"  - {message}" for message in self._validation_errors)
        elif self._validation_notes:
            lines.append("Validation checks:")
            lines.extend(f"  - {message}" for message in self._validation_notes)
        return lines

    def _credential_preview(self) -> List[str]:
        lines: List[str] = []
        client_email = str(self.config.credentials.get("client_email", ""))
        project_id = str(self.config.credentials.get("project_id", ""))
        token_uri = str(self.config.credentials.get("token_uri", ""))
        if client_email:
            lines.append(f"Service account: {_mask_value(client_email)}")
        if project_id:
            lines.append(f"Project ID: {_mask_value(project_id)}")
        if token_uri:
            lines.append(f"Token URI: {token_uri}")
        if "scopes" in self.config.credentials:
            scopes = self.config.credentials.get("scopes")
            if isinstance(scopes, list):
                lines.append(f"Stored scopes: {', '.join(str(scope) for scope in scopes)}")
        return lines

    # ------------------------------------------------------------------
    # Interactive helpers

    def configure_interactive(self) -> Tuple[List[str], List[str]]:
        """Prompt for configuration updates and return change and note lines."""

        print("\nGoogle Drive module setup")
        print("Follow the prompts to enable the module and provide connection details.")
        print("A Google Cloud service account with Drive API access is recommended.")

        changes: List[str] = []
        notes: List[str] = []

        enabled = _prompt_yes_no(
            "Enable the dedicated Google Drive module?",
            default=self.config.enabled,
        )
        if enabled != self.config.enabled:
            self.config.enabled = enabled
            changes.append("Drive module enabled" if enabled else "Drive module disabled")

        if not self.config.enabled:
            notes.append("Module left disabled; no configuration captured.")
            return changes, notes

        if _prompt_yes_no(
            "Update stored Google Drive credentials?",
            default=not self.config.has_credentials(),
        ):
            updated = self._capture_credentials()
            if updated:
                changes.append("Stored Google Drive credentials updated")
            else:
                notes.append("Credentials unchanged; previous values retained.")

        roots_prompt = "Comma separated Drive folder or shared drive IDs"
        roots_value = _prompt_text(roots_prompt, default=", ".join(self.config.root_ids))
        new_root_ids = [value.strip() for value in roots_value.split(",") if value.strip()]
        if new_root_ids != self.config.root_ids:
            self.config.root_ids = new_root_ids
            changes.append("Updated Drive root IDs")

        include_shared_with_me = _prompt_yes_no(
            "Include the 'Shared with me' section during crawls?",
            default=self.config.include_shared_with_me,
        )
        if include_shared_with_me != self.config.include_shared_with_me:
            self.config.include_shared_with_me = include_shared_with_me
            changes.append(
                "Enabled 'Shared with me' crawl"
                if include_shared_with_me
                else "Disabled 'Shared with me' crawl"
            )

        include_shared_drives = _prompt_yes_no(
            "Include shared drives during crawls?",
            default=self.config.include_shared_drives,
        )
        if include_shared_drives != self.config.include_shared_drives:
            self.config.include_shared_drives = include_shared_drives
            changes.append(
                "Enabled shared drive traversal"
                if include_shared_drives
                else "Disabled shared drive traversal"
            )

        whitelist_prompt = "MIME type whitelist (leave blank for all, comma separated)"
        whitelist_raw = _prompt_text(whitelist_prompt, default=", ".join(self.config.mime_whitelist))
        new_whitelist = [value.strip() for value in whitelist_raw.split(",") if value.strip()]
        if new_whitelist != self.config.mime_whitelist:
            self.config.mime_whitelist = new_whitelist
            if new_whitelist:
                changes.append("Updated MIME whitelist")
            else:
                changes.append("Cleared MIME whitelist")

        allow_writes = self.config.allow_writes
        write_prompt = "Enable write operations (updates/deletions) after confirming?"
        if _prompt_yes_no(write_prompt, default=allow_writes):
            if not allow_writes:
                confirmed = _prompt_yes_no(
                    "Are you absolutely sure you want to allow write access?",
                    default=False,
                )
                if confirmed:
                    self.config.allow_writes = True
                    changes.append("Write access enabled")
                else:
                    notes.append("Write access remains disabled pending confirmation.")
            else:
                notes.append("Write access already enabled; no change made.")
        else:
            if allow_writes:
                self.config.allow_writes = False
                changes.append("Write access disabled")

        notes.append(
            "Stored credentials are kept in config/google_drive_module.json and reused automatically."
        )
        notes.append(
            "Use the Drive root IDs to limit enumeration scope; leave empty to configure later."
        )
        return changes, notes

    def _capture_credentials(self) -> bool:
        """Capture service account credentials from a file or manual paste."""

        while True:
            source = _prompt_text(
                "Enter path to credentials JSON (or type 'paste' to input manually, 'skip' to keep current)",
                default=self.config.credentials_path or "paste",
            ).strip()
            if not source or source.lower() == "skip":
                return False
            if source.lower() == "paste":
                raw = _prompt_multiline(
                    "Paste the full service account JSON (blank line to finish)"
                )
                if not raw:
                    print("No input received; credentials unchanged.")
                    return False
            else:
                path = Path(source).expanduser()
                if not path.exists():
                    print(f"File not found: {path}")
                    continue
                raw = path.read_text(encoding="utf-8")
                self.config.credentials_path = str(path)
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"Unable to parse credentials JSON: {exc}")
                continue
            if not isinstance(parsed, dict):
                print("Credentials JSON must define an object at the top level.")
                continue
            required = {"type", "client_email", "private_key"}
            missing = sorted(required - set(parsed))
            if missing:
                print(f"Credentials JSON missing keys: {', '.join(missing)}")
                continue
            if parsed.get("type") not in {"service_account", "authorized_user"}:
                print("Warning: Credentials type is not 'service_account'.")
            self.config.credentials = parsed
            if source.lower() == "paste":
                self.config.credentials_path = ""
            return True

    # ------------------------------------------------------------------
    # Connection helpers

    def test_connection(self, *, require_write: bool = False) -> Tuple[bool, List[str]]:
        """Validate credentials with live Drive API calls."""

        if not self.config.enabled:
            return False, ["Module is disabled; enable it before testing the connection."]
        if not self.config.has_credentials():
            return False, ["No credentials stored; import a service account JSON first."]

        required_keys = {"type", "client_email", "private_key"}
        missing = sorted(key for key in required_keys if key not in self.config.credentials)
        if missing:
            return False, [f"Stored credentials are missing keys: {', '.join(missing)}"]

        roots = self.root_ids()
        if not roots:
            return False, ["No Drive root IDs configured. Provide at least one folder or shared drive ID."]

        service, error = self.ensure_service(require_write=require_write)
        if not service:
            return False, [error]

        lines: List[str] = []
        try:
            about = service.about().get(
                fields="user, storageQuota, kind, importFormats"
            ).execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return False, [f"Unable to query Drive API: {_format_http_error(exc)}"]

        user_info = about.get("user", {})
        storage = about.get("storageQuota", {})
        client_email = str(self.config.credentials.get("client_email", ""))
        project_id = str(self.config.credentials.get("project_id", ""))
        lines.extend(
            [
                "Credentials JSON validated successfully.",
                f"Service account: {client_email or 'unknown'}",
                f"Project ID: {project_id or 'unknown'}",
                f"Drive user: {user_info.get('displayName', 'unknown')} <{user_info.get('emailAddress', 'unknown')}>",
                f"Storage usage: {storage.get('usage', 'unknown')} / {storage.get('limit', 'unknown')} bytes",
                f"Configured root IDs: {', '.join(roots)}",
                f"Shared drives enabled: {'yes' if self.config.include_shared_drives else 'no'}",
                f"'Shared with me' enabled: {'yes' if self.config.include_shared_with_me else 'no'}",
            ]
        )

        if self.config.mime_whitelist:
            lines.append(f"MIME whitelist active: {', '.join(self.config.mime_whitelist)}")
        else:
            lines.append("MIME whitelist not set; all types allowed.")

        root_reports: List[str] = []
        for root_id in roots:
            try:
                metadata = service.files().get(
                    fileId=root_id,
                    fields="id, name, mimeType, driveId",
                    supportsAllDrives=True,
                ).execute()
            except Exception as exc:  # pragma: no cover - network dependent
                root_reports.append(f"Root {root_id}: unable to fetch metadata ({_format_http_error(exc)})")
            else:
                root_reports.append(
                    "Root {id} — {name} ({mime})".format(
                        id=metadata.get("id", root_id),
                        name=metadata.get("name", "unknown"),
                        mime=metadata.get("mimeType", "unknown"),
                    )
                )
        lines.append("Reachable roots:")
        lines.extend(f"  • {entry}" for entry in root_reports)

        if self.config.allow_writes:
            lines.append("Write access is enabled — destructive operations require explicit opt-in per command.")
        else:
            lines.append("Module is currently operating in read-only mode.")

        if require_write and not self.config.allow_writes:
            lines.append("Write scope was not requested because module write access is disabled.")

        lines.append("Live Drive API calls completed successfully.")
        return True, lines

    # ------------------------------------------------------------------
    # Read/write helpers with dry-run support

    def crawl(
        self,
        *,
        page_size: Optional[int] = None,
        max_depth: Optional[int] = None,
    ) -> Iterable[Dict[str, object]]:
        service, error = self.ensure_service()
        if not service:
            yield {"status": "error", "detail": error}
            return
        depth_limit = self.config.max_depth if max_depth is None else max_depth
        size = self.config.page_size if page_size is None else page_size
        mime_whitelist = set(self.config.mime_whitelist)
        include_trashed = True

        from collections import deque

        queue = deque([(root_id, 0) for root_id in self.root_ids()])
        visited: set[str] = set()
        while queue:
            current_id, depth = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
            try:
                current = (
                    service.files()
                    .get(
                        fileId=current_id,
                        fields="id, name, mimeType, parents, trashed, driveId, size, shortcutDetails",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            except Exception as exc:  # pragma: no cover - network dependent
                yield {"id": current_id, "status": "error", "detail": _format_http_error(exc)}
                continue
            yield current
            shortcut = current.get("shortcutDetails", {}) or {}
            target_id = shortcut.get("targetId") if isinstance(shortcut, dict) else None
            if target_id and target_id not in visited:
                queue.append((target_id, depth))
                continue
            if current.get("mimeType") != "application/vnd.google-apps.folder":
                continue
            if depth_limit and depth >= depth_limit:
                continue
            q_parts = [f"'{current_id}' in parents"]
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
                            includeItemsFromAllDrives=self.config.include_shared_drives,
                            supportsAllDrives=True,
                            corpora="allDrives" if self.config.include_shared_drives else "default",
                            pageSize=size,
                            pageToken=page_token,
                            fields="nextPageToken, files(id)",
                        )
                        .execute()
                    )
                except Exception as exc:  # pragma: no cover - network dependent
                    yield {
                        "parent": current_id,
                        "status": "error",
                        "detail": _format_http_error(exc),
                    }
                    break
                for child in response.get("files", []):
                    queue.append((child.get("id"), depth + 1))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        if self.config.include_shared_with_me:
            yield from self._list_shared_with_me(service, page_size=size)

    def download_file(self, file_id: str, destination: Path, *, dry_run: bool = True) -> Dict[str, object]:
        service, error = self.ensure_service()
        if not service:
            return {"status": "error", "detail": error}
        if dry_run:
            return {"status": "dry_run", "detail": f"Would download {file_id} to {destination}"}
        try:
            from googleapiclient.http import MediaIoBaseDownload  # Local import to avoid unused when dry-run
        except Exception:  # pragma: no cover - dependency guard
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
        write_guard = self._write_guard()
        if write_guard:
            return {"status": "error", "detail": write_guard}
        service, error = self.ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
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
                matches = (
                    service.files()
                    .list(
                        q=f"name = '{source.name}'",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                        corpora="allDrives" if self.config.include_shared_drives else "default",
                        pageSize=1,
                        fields="files(id)",
                    )
                    .execute()
                )
                files = matches.get("files", [])
                if files:
                    file_id = files[0].get("id")
                    response = (
                        service.files()
                        .update(fileId=file_id, media_body=media, supportsAllDrives=True)
                        .execute()
                    )
                    return {"status": "ok", "detail": "Updated existing file", "file": response}
            response = (
                service.files()
                .create(body=body, media_body=media, fields="id, name", supportsAllDrives=True)
                .execute()
            )
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
        write_guard = self._write_guard()
        if write_guard:
            return {"status": "error", "detail": write_guard}
        service, error = self.ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
        if dry_run:
            return {
                "status": "dry_run",
                "detail": f"Would update {file_id} with metadata {metadata}",
            }
        try:
            response = (
                service.files()
                .update(fileId=file_id, body=metadata, supportsAllDrives=True)
                .execute()
            )
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": "Updated metadata", "file": response}

    def delete_file(self, file_id: str, *, dry_run: bool = True) -> Dict[str, object]:
        write_guard = self._write_guard()
        if write_guard:
            return {"status": "error", "detail": write_guard}
        service, error = self.ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
        if dry_run:
            return {"status": "dry_run", "detail": f"Would delete file {file_id}"}
        try:
            service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": f"Deleted file {file_id}"}

    def update_permissions(
        self,
        file_id: str,
        *,
        role: str,
        permission_type: str,
        email: Optional[str] = None,
        domain: Optional[str] = None,
        allow_notification: bool = False,
        dry_run: bool = True,
    ) -> Dict[str, object]:
        write_guard = self._write_guard()
        if write_guard:
            return {"status": "error", "detail": write_guard}
        service, error = self.ensure_service(require_write=True)
        if not service:
            return {"status": "error", "detail": error}
        body: Dict[str, object] = {"role": role, "type": permission_type}
        if email:
            body["emailAddress"] = email
        if domain:
            body["domain"] = domain
        if dry_run:
            return {
                "status": "dry_run",
                "detail": f"Would add permission {body} to {file_id}",
            }
        try:
            response = (
                service.permissions()
                .create(
                    fileId=file_id,
                    body=body,
                    sendNotificationEmail=allow_notification,
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - network dependent
            return {"status": "error", "detail": _format_http_error(exc)}
        return {"status": "ok", "detail": "Permission added", "permission": response}

    def _determine_corpora_mode(self) -> str:
        if self.shared_drive_id:
            return "drive"
        if self.config.include_shared_drives:
            return "allDrives"
        return "default"

    def _describe_corpora_mode(self) -> str:
        if self._corpora_mode == "drive":
            drive_detail = self.shared_drive_id or "(not set)"
            return f"drive (driveId={drive_detail})"
        if self._corpora_mode == "allDrives":
            return "allDrives (supportsAllDrives=True)"
        return "default (My Drive only)"

    def _validate_environment(self) -> None:
        self._validation_errors = []
        self._validation_notes = []
        self._corpora_mode = self._determine_corpora_mode()

        self._validation_notes.append(f"Corpora mode active: {self._describe_corpora_mode()}")
        if self.shared_drive_id and not self.config.include_shared_drives:
            self._validation_notes.append(
                "Shared drive ID set; using corpora=drive overrides include_shared_drives settings."
            )

        root_id = self.fallback_root_id
        if not root_id:
            self._validation_notes.append(
                "DRIVE_ROOT_FOLDER_ID not provided; configure this environment variable to supply a fallback root."
            )
            return

        if not self.config.enabled or not self.config.has_credentials():
            self._validation_errors.append(
                "Cannot validate DRIVE_ROOT_FOLDER_ID because the Drive module is disabled or missing credentials. "
                "Hint: run 'Configure Google Drive module' and store service-account credentials."
            )
            return

        service, error = self.ensure_service()
        if not service:
            hint = error or "Drive client could not be created"
            self._validation_errors.append(
                f"Unable to validate DRIVE_ROOT_FOLDER_ID: {hint}. Hint: re-run Drive module configuration."
            )
            return

        try:
            metadata = (
                service.files()
                .get(
                    fileId=root_id,
                    fields="id, name, mimeType, driveId",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - network dependent
            message = _format_http_error(exc)
            self._validation_errors.append(
                f"Unable to reach DRIVE_ROOT_FOLDER_ID '{root_id}': {message}. "
                "Hint: confirm the folder ID and verify the service account has at least viewer access."
            )
            return

        display_name = metadata.get("name") or "(untitled)"
        drive_id = metadata.get("driveId")

        if self._corpora_mode == "drive":
            if not drive_id:
                self._validation_errors.append(
                    "Corpora mode 'drive' is active but DRIVE_ROOT_FOLDER_ID resolves to a My Drive folder. "
                    "Hint: clear DRIVE_SHARED_DRIVE_ID or choose a folder from the shared drive."
                )
                return
            if self.shared_drive_id and drive_id != self.shared_drive_id:
                self._validation_errors.append(
                    "DRIVE_ROOT_FOLDER_ID belongs to shared drive {actual} but DRIVE_SHARED_DRIVE_ID is {expected}. "
                    "Hint: update DRIVE_SHARED_DRIVE_ID to {actual} or pick a folder within the configured drive."
                    .format(actual=drive_id, expected=self.shared_drive_id)
                )
                return
            self._validation_notes.append(f"Using corpora=drive with driveId={drive_id}.")
        elif drive_id:
            if self._corpora_mode == "default":
                self._validation_errors.append(
                    "DRIVE_ROOT_FOLDER_ID is on shared drive {drive_id} but corpora mode is 'default'. "
                    "Hint: set DRIVE_SHARED_DRIVE_ID to {drive_id} or enable shared drives in the module so corpora=allDrives is used."
                    .format(drive_id=drive_id)
                )
                return
            self._validation_notes.append(
                f"Shared drive {drive_id} will be accessed via corpora=allDrives with supportsAllDrives=True."
            )
        elif self.shared_drive_id:
            self._validation_errors.append(
                "DRIVE_SHARED_DRIVE_ID is set but DRIVE_ROOT_FOLDER_ID is not part of that shared drive. "
                "Hint: provide a folder ID from the shared drive or remove DRIVE_SHARED_DRIVE_ID."
            )
            return

        detail = f"Validated DRIVE_ROOT_FOLDER_ID '{root_id}' ({display_name})"
        if drive_id:
            detail += f" on drive {drive_id}"
        self._validation_notes.append(detail)

    # ------------------------------------------------------------------
    # Internal helpers

    def _write_guard(self) -> Optional[str]:
        if not self.config.allow_writes:
            return "Write operations are disabled; enable them in the Drive module configuration."
        return None

    def _list_shared_with_me(self, service: object, page_size: int) -> Iterable[Dict[str, object]]:
        page_token: Optional[str] = None
        while True:
            try:
                response = (
                    service.files()
                    .list(
                        q="sharedWithMe",
                        includeItemsFromAllDrives=self.config.include_shared_drives,
                        supportsAllDrives=True,
                        corpora="allDrives" if self.config.include_shared_drives else "default",
                        pageToken=page_token,
                        pageSize=page_size,
                        fields="nextPageToken, files(id, name, mimeType, owners, sharedWithMeTime)",
                    )
                    .execute()
                )
            except Exception as exc:  # pragma: no cover - network dependent
                yield {"status": "error", "detail": _format_http_error(exc)}
                return
            for file_obj in response.get("files", []):
                yield file_obj
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    # ------------------------------------------------------------------
    # Utility helpers

    @staticmethod
    def _mask_path(value: str) -> str:
        if not value:
            return ""
        path = Path(value)
        if path.name:
            return f"…/{path.name}"
        return value


def _prompt_text(message: str, default: str | None = None) -> str:
    prompt = message
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    value = input(prompt).strip()
    if value:
        return value
    return default or ""


def _prompt_yes_no(message: str, default: bool | None = None) -> bool:
    if default is None:
        suffix = " [y/n]"
    elif default:
        suffix = " [Y/n]"
    else:
        suffix = " [y/N]"
    prompt = f"{message}{suffix}: "
    while True:
        answer = input(prompt).strip().lower()
        if not answer and default is not None:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")


def _prompt_multiline(message: str) -> str:
    print(message)
    print("Enter a blank line to finish input.")
    lines: List[str] = []
    while True:
        try:
            line = input()
        except EOFError:  # pragma: no cover - defensive
            break
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def _clean_list(value: object, allow_empty: bool = False) -> List[str]:
    if value is None:
        return [] if allow_empty else []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        items = [token.strip() for token in value.split(",") if token.strip()]
        return items
    return []


def _format_http_error(error: Exception) -> str:
    if isinstance(error, HttpError):  # pragma: no branch - type guard
        try:
            payload = json.loads(error.content.decode("utf-8")) if getattr(error, "content", None) else {}
        except Exception:  # pragma: no cover - defensive
            payload = {}
        if isinstance(payload, dict):
            message = payload.get("error", {}).get("message")
            if message:
                return message
        return getattr(error, "message", str(error))
    return str(error)


def _mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"
