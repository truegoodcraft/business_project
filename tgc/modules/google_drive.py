"""Interactive Google Drive module configuration helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_MODULE_CONFIG = Path("config/google_drive_module.json")


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

    def __init__(self, config: DriveModuleConfig, config_path: Path = DEFAULT_MODULE_CONFIG) -> None:
        self.config = config
        self.config_path = config_path

    # ------------------------------------------------------------------
    # Persistence helpers

    @classmethod
    def load(cls, path: Path = DEFAULT_MODULE_CONFIG) -> "GoogleDriveModule":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        config = DriveModuleConfig.from_dict(data)
        return cls(config=config, config_path=path)

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

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
        if self.config.root_ids:
            lines.append(f"- Root IDs ({len(self.config.root_ids)}): {', '.join(self.config.root_ids)}")
        else:
            lines.append("- Root IDs: not configured")
        lines.append(
            f"- Include 'Shared with me': {'yes' if self.config.include_shared_with_me else 'no'}"
        )
        lines.append(f"- Include shared drives: {'yes' if self.config.include_shared_drives else 'no'}")
        if self.config.mime_whitelist:
            lines.append(f"- MIME whitelist: {', '.join(self.config.mime_whitelist)}")
        else:
            lines.append("- MIME whitelist: all types")
        lines.append(f"- Allow write operations: {'yes' if self.config.allow_writes else 'no'}")
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
        if self.config.root_ids:
            lines.append("Configured root IDs:")
            lines.extend(f"  - {value}" for value in self.config.root_ids)
        else:
            lines.append("Configured root IDs: (none)")
        if self.config.mime_whitelist:
            lines.append("MIME whitelist:")
            lines.extend(f"  - {value}" for value in self.config.mime_whitelist)
        else:
            lines.append("MIME whitelist: (all)")
        if self.config.credentials_path:
            lines.append(
                f"Original credentials file: {self._mask_path(self.config.credentials_path)}"
            )
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

    def test_connection(self) -> Tuple[bool, List[str]]:
        """Perform lightweight validation of the provided configuration."""

        if not self.config.enabled:
            return False, ["Module is disabled; enable it before testing the connection."]
        if not self.config.has_credentials():
            return False, ["No credentials stored; import a service account JSON first."]

        required_keys = {"type", "client_email", "private_key"}
        missing = sorted(key for key in required_keys if key not in self.config.credentials)
        if missing:
            return False, [f"Stored credentials are missing keys: {', '.join(missing)}"]

        if not self.config.root_ids:
            return False, ["No Drive root IDs configured. Provide at least one folder or shared drive ID."]

        client_email = str(self.config.credentials.get("client_email", ""))
        project_id = str(self.config.credentials.get("project_id", ""))
        summary = [
            "Credentials JSON validated successfully.",
            f"Service account: {client_email or 'unknown'}",
            f"Project ID: {project_id or 'unknown'}",
            f"Configured root IDs: {', '.join(self.config.root_ids)}",
            f"Shared drives enabled: {'yes' if self.config.include_shared_drives else 'no'}",
            f"'Shared with me' enabled: {'yes' if self.config.include_shared_with_me else 'no'}",
        ]
        if self.config.mime_whitelist:
            summary.append(f"MIME whitelist active: {', '.join(self.config.mime_whitelist)}")
        else:
            summary.append("MIME whitelist not set; all types allowed.")
        if self.config.allow_writes:
            summary.append(
                "Write access is enabled — ensure least-privilege permissions are used."
            )
        else:
            summary.append("Module is currently operating in read-only mode.")
        summary.append(
            "No API calls were made; full Drive access requires running the dedicated module."
        )
        return True, summary

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


def _mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}***{value[-3:]}"
