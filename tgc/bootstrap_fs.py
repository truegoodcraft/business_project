# SPDX-License-Identifier: AGPL-3.0-or-later
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
TOKEN_FILE = DATA / "session_token.txt"

_ENV_SKELETON = """# === TGC Alpha Core .env ===
GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json
DRIVE_ROOT_IDS=
SHEET_INVENTORY_ID=
# NOTION_TOKEN=
# NOTION_ROOT_PAGE_IDS=
"""


def ensure_dirs() -> None:
    for path in (CREDENTIALS, DATA, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def ensure_env_skeleton() -> bool:
    if DOTENV.exists():
        return False
    DOTENV.write_text(_ENV_SKELETON, encoding="utf-8")
    return True


def _read_json_head(path: Path) -> Dict[str, str]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return {
            "type": str(obj.get("type", "")),
            "client_email": str(obj.get("client_email", "")),
            "project_id": str(obj.get("project_id", "")),
        }
    except Exception:
        return {}


def detect_credentials() -> Tuple[bool, Dict[str, str], str]:
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if env_path and not Path(env_path).is_absolute():
        abs_path = (ROOT / env_path).resolve()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_path)
        env_path = str(abs_path)
    candidates = [Path(env_path)] if env_path else []
    candidates.append(CREDENTIALS / "service-account.json")
    for cand in candidates:
        cand = Path(cand)
        if cand.exists():
            meta = _read_json_head(cand)
            if meta.get("type") == "service_account":
                return True, meta, f"Using credentials at: {cand}"
            return False, meta, (
                "Credentials found but not a service account JSON: "
                f"{cand}"
            )
    return (
        False,
        {},
        "Missing credentials. Drop service account JSON at: "
        f"{(CREDENTIALS / 'service-account.json')} and set GOOGLE_APPLICATION_CREDENTIALS (see .env).",
    )


def ensure_first_run() -> Dict[str, str]:
    ensure_dirs()
    created_env = ensure_env_skeleton()
    present, meta, hint = detect_credentials()
    return {
        "env_created": "yes" if created_env else "no",
        "creds_present": "yes" if present else "no",
        "creds_email": meta.get("client_email", ""),
        "creds_project": meta.get("project_id", ""),
        "hint": hint,
    }
