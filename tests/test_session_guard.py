# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from core.version import VERSION

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api import http
from core.api.http import TOKEN_HEADER, _extract_token, _require_session


def make_request(path: str = "/dev/writes", headers: dict[str, str] | None = None) -> Request:
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for key, value in headers.items():
            raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": raw_headers,
    }
    return Request(scope)


def test_extract_token_present() -> None:
    req = make_request(headers={TOKEN_HEADER: "abc123"})
    assert _extract_token(req) == "abc123"


def test_extract_token_missing() -> None:
    req = make_request()
    assert _extract_token(req) is None


def test_require_session_missing_token() -> None:
    req = make_request()
    response = asyncio.run(_require_session(req))
    assert response is not None
    assert response.status_code == 401
    assert json.loads(response.body.decode()) == {"error": "unauthorized"}


def test_require_session_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "invalid"
    req = make_request(headers={TOKEN_HEADER: token})
    monkeypatch.setattr(http, "validate_session_token", lambda _token: False)
    response = asyncio.run(_require_session(req))
    assert response is not None
    assert response.status_code == 401
    assert json.loads(response.body.decode()) == {"error": "unauthorized"}


def test_require_session_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "valid-token"
    req = make_request(headers={TOKEN_HEADER: token})
    monkeypatch.setattr(http, "validate_session_token", lambda candidate: candidate == token)
    response = asyncio.run(_require_session(req))
    assert response is None
    assert getattr(req.state, "session") == token


@pytest.fixture
def test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(http, "SESSION_TOKEN", "fixture-token", raising=False)
    monkeypatch.setattr(http, "_load_or_create_token", lambda: "fixture-token", raising=False)
    with TestClient(http.APP) as client:
        yield client


def test_integration_routes_and_cors(test_client: TestClient) -> None:
    token_resp = test_client.get("/session/token")
    assert token_resp.status_code == 200
    token = token_resp.json()["token"]
    assert token == "fixture-token"

    unauthorized_health = test_client.get("/health")
    assert unauthorized_health.status_code == 200
    assert unauthorized_health.json() == {"ok": True, "version": VERSION}

    unauthorized_writes = test_client.get("/dev/writes")
    assert unauthorized_writes.status_code == 401
    assert unauthorized_writes.json() == {"error": "unauthorized"}

    headers = {TOKEN_HEADER: token}
    health = test_client.get("/health", headers=headers)
    assert health.status_code == 200
    assert health.json() == {"ok": True, "version": VERSION}

    writes = test_client.get("/dev/writes", headers=headers)
    assert writes.status_code == 200
    body = writes.json()
    assert "enabled" in body

    options = test_client.options(
        "/dev/writes",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": TOKEN_HEADER,
        },
    )
    assert options.status_code == 200
    allow_headers = options.headers.get("access-control-allow-headers", "")
    assert TOKEN_HEADER.lower() in allow_headers.lower()
