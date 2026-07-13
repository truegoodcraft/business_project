# Copyright (C) 2025 BUS Core Authors
# SPDX-License-Identifier: AGPL-3.0-or-later

def test_config_lifecycle(bus_client):
    client = bus_client["client"]

    # The canonical fixture establishes an isolated unclaimed-mode session.
    resp = client.get("/app/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "launcher" in data
    assert "ui" in data
    assert data["ui"]["theme"] in ["system", "light", "dark"]

    # 3. POST config (writes are enabled by the canonical fixture)
    new_theme = "light"
    # Toggle to make sure we change it
    if data["ui"]["theme"] == "light":
        new_theme = "dark"

    payload = {"ui": {"theme": new_theme}}
    resp = client.post("/app/config", json=payload)
    assert resp.status_code == 200
    assert resp.json()["restart_required"] is True

    # 4. Verify persistence via API
    resp = client.get("/app/config")
    assert resp.json()["ui"]["theme"] == new_theme

    # 5. Verify persistence via manager directly
    from core.config.manager import load_config
    c = load_config()
    assert c.ui.theme == new_theme

    # Restore default
    client.post("/app/config", json={"ui": {"theme": "system"}})
