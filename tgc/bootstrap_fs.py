from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS = ROOT / "credentials"
DATA = ROOT / "data"
LOGS = ROOT / "logs"
DOTENV = ROOT / ".env"

_ENV_SKELETON = """# === TGC Alpha Core .env ===
# Place your Google service account JSON at: credentials/service-account.json
# Then set the path below (relative or absolute):
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json

# List one or more Drive folder IDs (comma-separated) to probe/crawl
DRIVE_ROOT_IDS=

# Sheets inventory spreadsheet ID (optional for probe; required for sheets indexing)
SHEET_INVENTORY_ID=

# Notion (optional)
# NOTION_TOKEN=
# NOTION_ROOT_PAGE_IDS=
"""


def ensure_dirs() -> None:
    for p in (CREDENTIALS, DATA, LOGS):
        p.mkdir(parents=True, exist_ok=True)


def ensure_env_skeleton() -> bool:
    if DOTENV.exists():
        return False
    DOTENV.write_text(_ENV_SKELETON, encoding="utf-8")
    return True


def _read_json_head(path: Path) -> Dict[str, str]:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        return {
            "type": str(obj.get("type", "")),
            "client_email": str(obj.get("client_email", "")),
            "project_id": str(obj.get("project_id", "")),
        }
    except Exception:
        return {}


def detect_credentials() -> Tuple[bool, Dict[str, str], str]:
    """Returns (present, meta, hint)."""

    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if env_path and not Path(env_path).is_absolute():
        env_path = str((ROOT / env_path).resolve())
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = env_path

    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(CREDENTIALS / "service-account.json")

    for cand in candidates:
        if cand.exists():
            meta = _read_json_head(cand)
            if meta.get("type") == "service_account":
                return True, meta, f"Using credentials at: {cand}"
            return False, meta, (
                "Credentials file found but not a service account JSON: " f"{cand}"
            )
    return (
        False,
        {},
        "Missing credentials. Drop your service account JSON at: "
        f"{CREDENTIALS / 'service-account.json'} and set GOOGLE_APPLICATION_CREDENTIALS "
        "accordingly (see .env).",
    )


def ensure_first_run() -> Dict[str, str]:
    """Make project writable paths & scaffold .env; return a status dict with hints."""

    ensure_dirs()
    created_env = ensure_env_skeleton()
    present, meta, hint = detect_credentials()
    status = {
        "env_created": "yes" if created_env else "no",
        "creds_present": "yes" if present else "no",
        "creds_email": meta.get("client_email", ""),
        "creds_project": meta.get("project_id", ""),
        "hint": hint,
    }
    return status
