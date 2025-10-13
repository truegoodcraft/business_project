import types

from core.conn_broker import ConnectionBroker


class _DriveService:
    def files(self):
        return types.SimpleNamespace(
            list=lambda **kwargs: types.SimpleNamespace(execute=lambda: {"files": [{"id": "1"}]}),
            get=lambda **kwargs: types.SimpleNamespace(execute=lambda: {"id": "1"}),
        )


class _DriveModule:
    def __init__(self):
        self.config = types.SimpleNamespace(
            mime_whitelist=[],
            max_depth=0,
            page_size=100,
            root_ids=["root"],
        )
        self.calls = []

    def ensure_service(self, require_write: bool = False):
        self.calls.append(require_write)
        return _DriveService(), None

    def root_ids(self):
        return ["root"]


class _NotionModule:
    def __init__(self):
        self.config = types.SimpleNamespace(root_ids=["notion-root"], max_depth=0, page_size=10)

    def _build_client(self):
        return types.SimpleNamespace(
            databases_retrieve=lambda _id: {"title": []},
            users_me=lambda: {"name": "bot"},
        ), None


class _SheetsAdapter:
    def __init__(self):
        self.config = types.SimpleNamespace(inventory_sheet_id="sheet")

    def is_configured(self):
        return True

    def inventory_metadata(self, *, force_refresh: bool = False):
        return {"spreadsheetId": "sheet", "title": "Demo", "sheets": []}


class _Controller:
    def __init__(self):
        self.modules = {"drive": _DriveModule(), "notion_access": _NotionModule()}
        self.adapters = {"sheets": _SheetsAdapter()}


def test_conn_broker_scopes():
    controller = _Controller()
    broker = ConnectionBroker(controller)

    drive_base = broker.get_client("drive", scope="read_base")
    drive_crawl = broker.get_client("drive", scope="read_crawl")
    drive_write = broker.get_client("drive", scope="write")

    assert drive_base.scope == "read_base"
    assert drive_crawl.scope == "read_crawl"
    assert drive_write.scope == "write"
    assert controller.modules["drive"].calls == [False, False, True]

    notion_client = broker.get_client("notion", scope="read_base")
    assert notion_client.service == "notion"

    sheets_client = broker.get_client("sheets", scope="read_base")
    assert sheets_client.service == "sheets"

    assert broker.probe("drive")["ok"] is True
    assert broker.probe("notion")["ok"] is True
    assert broker.probe("sheets")["ok"] is True
