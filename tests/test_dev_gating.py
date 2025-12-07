# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from fastapi.testclient import TestClient
from core.api import http

def _client():
    return TestClient(http.app)

def _get_auth_headers(client: TestClient):
    r = client.get("/session/token")
    assert r.status_code == 200

    cookie_val = None
    if isinstance(r.headers, list):
        for k, v in r.headers:
            if k.lower() == "set-cookie":
                cookie_val = v
                break
    elif hasattr(r.headers, "getlist"):
        l = r.headers.getlist("set-cookie")
        if l: cookie_val = l[0]
    elif hasattr(r.headers, "get"):
        cookie_val = r.headers.get("set-cookie")

    if cookie_val:
        simple_cookie = cookie_val.split(";")[0]
        return {"Cookie": simple_cookie}
    return {}

def test_prod_mode_hides_dev_routes(monkeypatch):
    monkeypatch.setenv("BUS_DEV", "0")
    with _client() as c:
        headers = _get_auth_headers(c)
        r = c.get("/health/detailed", headers=headers)
        assert r.status_code == 404
        r = c.get("/dev/writes", headers=headers)
        assert r.status_code == 404

def test_dev_mode_flow(monkeypatch):
    monkeypatch.setenv("BUS_DEV", "1")

    # Debug: Print routes
    # for route in http.app.routes:
    #     print(f"Route: {route.path} {route.name}")

    with _client() as c:
        r = c.get("/health/detailed")
        assert r.status_code == 401

        headers = _get_auth_headers(c)

        r = c.get("/health/detailed", headers=headers)
        assert r.status_code == 200

        r = c.get("/dev/writes", headers=headers)
        if r.status_code != 200:
            print(f"FAILED /dev/writes: {r.status_code} {r.text}")
            # Print available routes if 404
            found = False
            for route in http.app.routes:
                if getattr(route, "path", "") == "/dev/writes":
                    found = True
            print(f"Route /dev/writes registered: {found}")

        assert r.status_code == 200
        r = c.post("/dev/writes", json={"enabled": True}, headers=headers)
        assert r.status_code == 404
