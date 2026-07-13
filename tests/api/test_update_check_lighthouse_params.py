# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ticket 2A: BUS Core sends aggregate-safe update-check params to Lighthouse.

The outbound update-check request must carry only ``current_version``,
``channel`` and ``first_check`` — a privacy-safe active-install proxy plus a
first-seen/repeat split, with no identity of any kind.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlsplit

import pytest

from core.config.manager import Config, UpdatesConfig
from core.services.update import UpdateService, _build_update_check_url
from core.version import VERSION as CURRENT_VERSION

pytestmark = pytest.mark.api


EXPECTED_RESPONSE_KEYS = {
    "current_version",
    "latest_version",
    "update_available",
    "download_url",
    "error_code",
    "error_message",
}

# Identity-bearing params that must never appear on the outbound request.
FORBIDDEN_QUERY_KEYS = {
    "install_id",
    "device_id",
    "user_id",
    "hostname",
    "username",
    "fingerprint",
    "machine_id",
    "dedupe",
    "dedupe_token",
    "client_id",
}


def _set_updates(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    channel: str = "stable",
    manifest_url: str = "https://example.test/manifest.json",
) -> None:
    from core.api.routes import update as update_routes

    updates = UpdatesConfig.model_construct(
        enabled=enabled,
        channel=channel,
        manifest_url=manifest_url,
        check_on_startup=True,
    )
    cfg = Config.model_construct(updates=updates)
    monkeypatch.setattr(update_routes, "load_config", lambda: cfg)


def _capture_service(recorded: list[str], *, version: str = "9.9.9") -> UpdateService:
    def _fetch(url: str, _timeout: float):
        recorded.append(url)
        return {"version": version, "download_url": "https://example.test/dl"}

    return UpdateService(fetch_manifest=_fetch)


def _set_first_reported(
    monkeypatch: pytest.MonkeyPatch,
    *,
    reported: bool,
    store: list[bool] | None = None,
) -> None:
    from core.api.routes import update as update_routes

    monkeypatch.setattr(update_routes, "get_update_check_first_reported", lambda: reported)

    def _record(value: bool) -> None:
        if store is not None:
            store.append(value)

    monkeypatch.setattr(update_routes, "set_update_check_first_reported", _record)


def _outbound_query(recorded: list[str]) -> list[tuple[str, str]]:
    assert recorded, "expected the update-check to reach the fetcher"
    return parse_qsl(urlsplit(recorded[0]).query, keep_blank_values=True)


# --- Outbound URL shape (points 1, 2, 3, 5, 10) --------------------------------


def test_outbound_url_first_check_true_carries_all_params(bus_client, monkeypatch):
    from core.api.routes import update as update_routes

    _set_updates(monkeypatch, enabled=True, channel="stable")
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    store: list[bool] = []
    _set_first_reported(monkeypatch, reported=False, store=store)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200

    query = dict(_outbound_query(recorded))
    # 1 + 2 + 3
    assert query["current_version"] == CURRENT_VERSION
    assert query["channel"] == "stable"
    assert query["first_check"] == "true"
    # 10: exactly the three aggregate-safe params, nothing identity-bearing.
    assert set(query.keys()) == {"current_version", "channel", "first_check"}
    assert FORBIDDEN_QUERY_KEYS.isdisjoint(query.keys())
    # 5: the first report is recorded after the attempt finishes.
    assert store == [True]


def test_later_check_sends_first_check_false_and_does_not_rewrite_flag(bus_client, monkeypatch):
    from core.api.routes import update as update_routes

    _set_updates(monkeypatch, enabled=True, channel="stable")
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    store: list[bool] = []
    _set_first_reported(monkeypatch, reported=True, store=store)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200

    query = dict(_outbound_query(recorded))
    assert query["first_check"] == "false"
    assert query["current_version"] == CURRENT_VERSION
    assert query["channel"] == "stable"
    # Already reported → we neither send true nor rewrite the flag.
    assert store == []


def test_channel_param_reflects_configured_channel(bus_client, monkeypatch):
    from core.api.routes import update as update_routes

    _set_updates(monkeypatch, enabled=True, channel="partner-3dque")
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    _set_first_reported(monkeypatch, reported=True)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200

    query = dict(_outbound_query(recorded))
    assert query["channel"] == "partner-3dque"


# --- First-check flag persistence (point 5) ------------------------------------


def test_first_reported_flag_persists_to_config(monkeypatch, tmp_path):
    from core.config import manager

    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr(manager, "config_path", lambda: cfg_file)

    assert manager.get_update_check_first_reported() is False
    manager.set_update_check_first_reported(True)
    assert manager.get_update_check_first_reported() is True

    on_disk = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert on_disk["update_check_first_reported"] is True


def test_first_reported_flag_survives_settings_round_trip(monkeypatch, tmp_path):
    from core.config import manager

    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr(manager, "config_path", lambda: cfg_file)

    manager.set_update_check_first_reported(True)
    # A normal settings save must not wipe the first-check state.
    manager.save_config({"updates": {"channel": "test"}})

    assert manager.get_update_check_first_reported() is True


# --- Existing manifest query params preserved (point 6) ------------------------


def test_existing_manifest_query_params_preserved(bus_client, monkeypatch):
    from core.api.routes import update as update_routes

    _set_updates(
        monkeypatch,
        enabled=True,
        channel="stable",
        manifest_url="https://example.test/manifest.json?foo=bar",
    )
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    _set_first_reported(monkeypatch, reported=False)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200

    query = dict(_outbound_query(recorded))
    assert query["foo"] == "bar"
    assert query["current_version"] == CURRENT_VERSION
    assert query["channel"] == "stable"
    assert query["first_check"] == "true"


def test_app_provided_values_win_over_manifest_duplicates():
    url = _build_update_check_url(
        "https://example.test/manifest.json?current_version=0.0.1&channel=beta&first_check=false&foo=bar",
        current_version="1.2.3",
        channel="stable",
        first_check=True,
    )
    pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    # No duplication: each app-owned key appears exactly once.
    assert keys.count("current_version") == 1
    assert keys.count("channel") == 1
    assert keys.count("first_check") == 1
    query = dict(pairs)
    assert query["current_version"] == "1.2.3"
    assert query["channel"] == "stable"
    assert query["first_check"] == "true"
    # Unrelated existing params are still preserved.
    assert query["foo"] == "bar"


# --- Invalid / missing version does not block (point 7) ------------------------


def test_invalid_version_is_omitted_but_url_still_built():
    url = _build_update_check_url(
        "https://example.test/manifest.json",
        current_version="not-a-semver",
        channel="stable",
        first_check=True,
    )
    query = dict(parse_qsl(urlsplit(url).query))
    assert "current_version" not in query
    assert query["channel"] == "stable"
    assert query["first_check"] == "true"


def test_missing_version_is_omitted_but_url_still_built():
    url = _build_update_check_url(
        "https://example.test/manifest.json",
        current_version=None,
        channel="stable",
        first_check=False,
    )
    query = dict(parse_qsl(urlsplit(url).query))
    assert "current_version" not in query
    assert query["first_check"] == "false"


def test_invalid_channel_falls_back_to_stable():
    url = _build_update_check_url(
        "https://example.test/manifest.json",
        current_version="1.2.3",
        channel="totally-invalid",
        first_check=None,
    )
    query = dict(parse_qsl(urlsplit(url).query))
    assert query["channel"] == "stable"
    # first_check omitted entirely when not applicable.
    assert "first_check" not in query


def test_url_building_never_raises_on_odd_input():
    # URL building must never raise; the downstream validator (not query
    # construction) decides whether an odd base URL is ultimately accepted.
    for base in ("", "not a url", "https://example.test/m.json"):
        result = _build_update_check_url(base, current_version="1.2.3", channel="stable", first_check=True)
        assert isinstance(result, str)


# --- Enable/disable behavior unchanged (point 8) -------------------------------


def test_disabled_updates_endpoint_behavior_unchanged(bus_client, monkeypatch):
    # Pre-existing contract: /app/update/check does not itself gate on the
    # updates.enabled flag. Ticket 2A must not change that behavior.
    from core.api.routes import update as update_routes

    _set_updates(monkeypatch, enabled=False, channel="stable")
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    _set_first_reported(monkeypatch, reported=True)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == EXPECTED_RESPONSE_KEYS
    # Behavior identical to before: the request still went out with our params.
    query = dict(_outbound_query(recorded))
    assert query["current_version"] == CURRENT_VERSION
    assert query["first_check"] == "false"


# --- Response contract unchanged (point 9) -------------------------------------


def test_response_contract_unchanged(bus_client, monkeypatch):
    from core.api.routes import update as update_routes

    _set_updates(monkeypatch, enabled=True, channel="stable")
    recorded: list[str] = []
    monkeypatch.setattr(update_routes, "get_update_service", lambda: _capture_service(recorded))
    _set_first_reported(monkeypatch, reported=False)

    response = bus_client["client"].get("/app/update/check")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == EXPECTED_RESPONSE_KEYS
    assert body["current_version"] == CURRENT_VERSION
    assert body["update_available"] is True
    assert body["download_url"] == "https://example.test/dl"


# --- No identity fields, ever (point 10) ---------------------------------------


def test_outbound_url_contains_no_identity_fields():
    url = _build_update_check_url(
        "https://example.test/manifest.json",
        current_version="1.2.3",
        channel="stable",
        first_check=True,
    )
    query_keys = {key for key, _ in parse_qsl(urlsplit(url).query)}
    assert query_keys == {"current_version", "channel", "first_check"}
    assert FORBIDDEN_QUERY_KEYS.isdisjoint(query_keys)
