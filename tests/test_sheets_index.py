import pytest

from tgc.actions.sheets_index import build_sheets_index

SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
FOLDER_MIME = "application/vnd.google-apps.folder"


def _drive_item(file_id, name, mime_type, *, modified="2024-01-01T00:00:00Z"):
    return {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "modifiedTime": modified,
    }


def test_build_sheets_index_collects_nested_metadata(monkeypatch):
    drive_payloads = {
        "root": [
            _drive_item("folder-1", "Reports", FOLDER_MIME),
            _drive_item("sheet-1", "Sales", SPREADSHEET_MIME, modified="2024-01-02T00:00:00Z"),
        ],
        "folder-1": [
            _drive_item("sheet-2", "Budget/2024", SPREADSHEET_MIME, modified="2024-01-03T00:00:00Z"),
        ],
    }

    drive_calls = []

    def fake_list(root_ids, *, limits=None, config=None):
        root = root_ids[0] if root_ids else None
        drive_calls.append((tuple(root_ids), limits))
        return [dict(entry) for entry in drive_payloads.get(root, [])]

    monkeypatch.setattr(
        "tgc.actions.sheets_index.drive_adapter.list_drive_files",
        fake_list,
    )

    metadata_map = {
        "sheet-1": {
            "spreadsheetId": "sheet-1",
            "title": "Sales Tracker",
            "sheets": [
                {"sheetId": 10, "title": "Summary", "index": 0, "rowCount": 20, "columnCount": 5},
                {"sheetId": 11, "title": "Data", "index": 1, "rowCount": 100, "columnCount": 8},
            ],
        },
        "sheet-2": {
            "spreadsheetId": "sheet-2",
            "title": "Budget",  # type: ignore[dict-item]
            "sheets": [
                {"sheetId": 12, "title": "Totals", "index": 0, "rowCount": 50, "columnCount": 6},
            ],
        },
    }

    metadata_calls = []

    def fake_metadata(spreadsheet_id, *, credentials, timeout):
        metadata_calls.append((spreadsheet_id, timeout))
        return dict(metadata_map[spreadsheet_id])

    monkeypatch.setattr(
        "tgc.actions.sheets_index.sheets_adapter.get_spreadsheet_metadata",
        fake_metadata,
    )

    config = {
        "drive_config": {"token": "token"},
        "sheets_credentials": {"client_email": "svc@example.com"},
        "quiet": True,
    }

    rows = build_sheets_index(None, "root", config)

    assert [row["spreadsheetId"] for row in rows] == ["sheet-1", "sheet-1", "sheet-2"]
    assert rows[0]["sheetTitle"] == "Summary"
    assert rows[1]["sheetTitle"] == "Data"
    assert rows[2]["parentPath"] == "/Reports"
    assert rows[2]["sheetTitle"] == "Totals"
    assert rows[2]["modifiedTime"] == "2024-01-03T00:00:00Z"
    assert rows[2]["url"] == "https://docs.google.com/spreadsheets/d/sheet-2"

    # Drive listed the root and then the child folder
    assert [call[0][0] for call in drive_calls] == ["root", "folder-1"]
    # Metadata requested for each spreadsheet
    assert [call[0] for call in metadata_calls] == ["sheet-1", "sheet-2"]


def test_build_sheets_index_respects_max_items(monkeypatch):
    drive_payloads = {
        "root": [
            _drive_item("sheet-1", "One", SPREADSHEET_MIME),
            _drive_item("sheet-2", "Two", SPREADSHEET_MIME),
        ]
    }

    monkeypatch.setattr(
        "tgc.actions.sheets_index.drive_adapter.list_drive_files",
        lambda root_ids, *, limits=None, config=None: [
            dict(entry) for entry in drive_payloads.get(root_ids[0], [])
        ],
    )

    def fake_metadata(spreadsheet_id, *, credentials, timeout):
        return {
            "spreadsheetId": spreadsheet_id,
            "title": spreadsheet_id,
            "sheets": [{"sheetId": 1, "title": "Sheet1", "index": 0, "rowCount": 1, "columnCount": 1}],
        }

    monkeypatch.setattr(
        "tgc.actions.sheets_index.sheets_adapter.get_spreadsheet_metadata",
        fake_metadata,
    )

    config = {
        "drive_config": {"token": "token"},
        "sheets_credentials": {"client_email": "svc@example.com"},
        "quiet": True,
    }

    rows = build_sheets_index({"max_items": 1}, "root", config)

    assert {row["spreadsheetId"] for row in rows} == {"sheet-1"}


def test_build_sheets_index_respects_max_requests(monkeypatch):
    def fake_list(root_ids, *, limits=None, config=None):
        return [_drive_item("sheet-1", "One", SPREADSHEET_MIME)]

    monkeypatch.setattr(
        "tgc.actions.sheets_index.drive_adapter.list_drive_files",
        fake_list,
    )

    metadata_called = False

    def fake_metadata(spreadsheet_id, *, credentials, timeout):  # pragma: no cover - should not run
        nonlocal metadata_called
        metadata_called = True
        return {}

    monkeypatch.setattr(
        "tgc.actions.sheets_index.sheets_adapter.get_spreadsheet_metadata",
        fake_metadata,
    )

    config = {
        "drive_config": {"token": "token"},
        "sheets_credentials": {"client_email": "svc@example.com"},
        "quiet": True,
    }

    rows = build_sheets_index({"max_requests": 1}, "root", config)

    assert rows == []
    assert metadata_called is False


def test_build_sheets_index_respects_max_seconds(monkeypatch):
    called = False

    def fake_list(root_ids, *, limits=None, config=None):  # pragma: no cover - should not run
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(
        "tgc.actions.sheets_index.drive_adapter.list_drive_files",
        fake_list,
    )

    monkeypatch.setattr(
        "tgc.actions.sheets_index.sheets_adapter.get_spreadsheet_metadata",
        lambda spreadsheet_id, *, credentials, timeout: {},
    )

    config = {
        "drive_config": {"token": "token"},
        "sheets_credentials": {"client_email": "svc@example.com"},
        "quiet": True,
    }

    rows = build_sheets_index({"max_seconds": 0}, "root", config)

    assert rows == []
    assert called is False
