from core.config import load_plugin_config
from core.plugin_api import Result
from tgc.master_index_controller import collect_notion_pages, TraversalResult


def _call_collect(module, root_ids, params) -> TraversalResult:
    kwargs = {k: v for k, v in params.items() if v is not None}
    return collect_notion_pages(module, root_ids, **kwargs)


def index_pages(ctx, **kw) -> Result:
    cfg = load_plugin_config("notion-plugin")
    _ = cfg["NOTION_TOKEN"]
    _ = cfg.get("NOTION_DB_INVENTORY_ID")

    module = kw.get("module")
    if module is None:
        return Result(ok=False, notes=["Notion module unavailable"])

    root_ids = kw.get("root_ids") or []
    params = {
        "max_depth": kw.get("max_depth"),
        "page_size": kw.get("page_size"),
        "limit": kw.get("limit"),
        "limits": kw.get("limits"),
    }

    try:
        traversal = _call_collect(module, root_ids, params)
    except Exception as exc:  # pragma: no cover - defensive logging
        ctx.logger.exception("notion.index_pages.failed", exc_info=exc)
        return Result(ok=False, notes=[str(exc)])

    return Result(ok=True, data=traversal)


def health(ctx) -> Result:  # pragma: no cover - lightweight placeholder
    _ = ctx
    return Result(ok=None, notes=["Health check not implemented"])
