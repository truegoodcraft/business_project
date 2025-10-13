from core.config import load_plugin_config
from core.plugin_api import Result
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from tgc.actions.sheets_index import build_sheets_index
from tgc.master_index_controller import collect_drive_files, TraversalResult


def _session(cfg):
    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    creds = service_account.Credentials.from_service_account_file(
        cfg["GOOGLE_APPLICATION_CREDENTIALS"], scopes=scopes
    )
    return AuthorizedSession(creds)


def _call_collect(module, root_ids, params) -> TraversalResult:
    kwargs = {k: v for k, v in params.items() if v is not None}
    return collect_drive_files(module, root_ids, **kwargs)


def list_drive_files(ctx, **kw) -> Result:
    cfg = load_plugin_config("google-plugin")
    _ = cfg["GOOGLE_APPLICATION_CREDENTIALS"]
    _ = cfg.get("DRIVE_ROOT_FOLDER_ID")

    module = kw.get("module")
    if module is None:
        return Result(ok=False, notes=["Drive module unavailable"])

    root_ids = kw.get("root_ids") or []
    params = {
        "mime_whitelist": kw.get("mime_whitelist"),
        "max_depth": kw.get("max_depth"),
        "page_size": kw.get("page_size"),
        "limit": kw.get("limit"),
        "limits": kw.get("limits"),
    }

    try:
        traversal = _call_collect(module, root_ids, params)
    except Exception as exc:  # pragma: no cover - defensive logging
        ctx.logger.exception("google.list_drive_files.failed", exc_info=exc)
        return Result(ok=False, notes=[str(exc)])

    return Result(ok=True, data=traversal)


def sheets_index(ctx, **kw) -> Result:
    cfg = load_plugin_config("google-plugin")
    _ = cfg["GOOGLE_APPLICATION_CREDENTIALS"]
    _ = cfg.get("DRIVE_ROOT_FOLDER_ID")
    _ = cfg.get("SHEET_INVENTORY_ID")

    config = kw.get("config")
    if config is None:
        return Result(ok=False, notes=["App configuration unavailable"])

    limits = kw.get("limits")
    root_ids = kw.get("root_ids") or []

    rows = []
    notes = []
    for root_id in root_ids:
        try:
            rows.extend(build_sheets_index(limits, root_id, config))
        except Exception as exc:  # pragma: no cover - defensive logging
            ctx.logger.exception("google.sheets_index.failed", exc_info=exc)
            notes.append(f"Sheets traversal failed for {root_id}: {exc}")

    if notes:
        return Result(ok=False, data=rows or None, notes=notes)

    return Result(ok=True, data=rows)
